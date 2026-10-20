"""Rotas de mercado: ativo (cotação + histórico + fundamentos), watchlist e comparação."""

from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from desktop.state import financial_agent
from desktop.streaming import require_llm, stream_text
from stonks_ai.collectors.stocks.base import StockCollectorError
from stonks_ai.database import db
from stonks_ai.llm.prompts import FINANCIAL_ANALYSIS_SYSTEM_PROMPT, format_stock_analysis_prompt
from stonks_ai.models.stock_history import StockQueryHistory
from stonks_ai.models.watchlist import WatchlistItem
from stonks_ai.utils.validators import detect_exchange

router = APIRouter(prefix="/api")

PERIODS = {"1mo", "3mo", "6mo", "1y", "2y", "5y"}


def _norm(ticker: str) -> str:
    return ticker.strip().upper()


def _history_points(ticker: str, period: str) -> List[Dict[str, Any]]:
    if period not in PERIODS:
        raise HTTPException(status_code=422, detail="Período inválido.")
    h = financial_agent().get_history(ticker, period=period)
    return [{"date": str(d["date"])[:10], "close": d["close"]} for d in h.data if d.get("close")]


def _safe(fn, *args):
    try:
        return fn(*args)
    except Exception:
        return None


# ── Ativo ───────────────────────────────────────────────────────────────

@router.get("/asset/{ticker}")
def asset(ticker: str, period: str = "6mo") -> Dict[str, Any]:
    """Cotação, fundamentos e histórico de um ativo, buscados em paralelo."""
    ticker = _norm(ticker)
    agent = financial_agent()
    with ThreadPoolExecutor(max_workers=3) as pool:
        f_quote = pool.submit(agent.get_quote, ticker)
        f_fund = pool.submit(_safe, agent.get_fundamentals, ticker)
        f_hist = pool.submit(_safe, _history_points, ticker, period)
        try:
            quote = f_quote.result()
        except StockCollectorError as e:
            raise HTTPException(status_code=404, detail=str(e))
        fund = f_fund.result()
        history = f_hist.result() or []

    with db.session() as session:
        watched = session.query(WatchlistItem).filter(WatchlistItem.ticker == quote.ticker).first()
        watch_id = watched.id if watched else None

    return {
        "quote": quote.to_dict(),
        "fundamentals": fund.to_dict() if fund else None,
        "history": history,
        "period": period,
        "watchlist_id": watch_id,
    }


@router.get("/asset/{ticker}/history")
def asset_history(ticker: str, period: str = "6mo") -> List[Dict[str, Any]]:
    try:
        return _history_points(_norm(ticker), period)
    except StockCollectorError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/asset/{ticker}/analysis")
def asset_analysis(ticker: str):
    """Análise do ativo pela IA, em streaming."""
    agent = financial_agent()
    require_llm(agent.llm)
    ticker = _norm(ticker)
    try:
        quote = agent.get_quote(ticker)
    except StockCollectorError as e:
        raise HTTPException(status_code=404, detail=str(e))
    fund = _safe(agent.get_fundamentals, ticker)
    prompt = format_stock_analysis_prompt(quote.to_dict(), fund.to_dict() if fund else None)

    def save(text: str) -> None:
        agent.save_to_history(StockQueryHistory(
            ticker=quote.ticker, exchange=quote.exchange,
            query_type="analysis", result_summary=text[:500],
        ))

    return stream_text(
        lambda: agent.llm.generate_stream(prompt, system_prompt=FINANCIAL_ANALYSIS_SYSTEM_PROMPT),
        on_complete=save,
    )


# ── Watchlist ───────────────────────────────────────────────────────────

class WatchlistIn(BaseModel):
    ticker: str = Field(min_length=1, max_length=20)
    target_price: Optional[float] = Field(default=None, gt=0)


class TargetIn(BaseModel):
    target_price: Optional[float] = Field(default=None, gt=0)


def _watchlist_row(item: Dict[str, Any]) -> Dict[str, Any]:
    row = {**item, "price": None, "change_percent": None, "currency": None, "name": "", "error": None}
    try:
        q = financial_agent().get_quote(item["ticker"], item["exchange"])
        row.update(price=q.price, change_percent=q.change_percent, currency=q.currency, name=q.name)
    except StockCollectorError as e:
        row["error"] = str(e)
    except Exception:
        row["error"] = "Cotação indisponível"
    return row


@router.get("/watchlist")
def watchlist() -> List[Dict[str, Any]]:
    """Watchlist com cotações (buscadas em paralelo)."""
    with db.session() as session:
        items = [
            {"id": i.id, "ticker": i.ticker, "exchange": i.exchange, "target_price": i.target_price}
            for i in session.query(WatchlistItem).order_by(WatchlistItem.added_at.desc()).all()
        ]
    if not items:
        return []
    with ThreadPoolExecutor(max_workers=min(8, len(items))) as pool:
        return list(pool.map(_watchlist_row, items))


@router.post("/watchlist", status_code=201)
def watchlist_add(body: WatchlistIn) -> Dict[str, Any]:
    ticker = _norm(body.ticker)
    exchange = detect_exchange(ticker)
    if exchange == "UNKNOWN":
        exchange = "B3"
    with db.session() as session:
        if session.query(WatchlistItem).filter(WatchlistItem.ticker == ticker).first():
            raise HTTPException(status_code=409, detail=f"{ticker} já está na watchlist.")
        item = WatchlistItem(ticker=ticker, exchange=exchange, target_price=body.target_price)
        session.add(item)
        session.flush()
        return {"id": item.id, "ticker": ticker, "exchange": exchange}


@router.patch("/watchlist/{item_id}")
def watchlist_target(item_id: int, body: TargetIn) -> Dict[str, Any]:
    with db.session() as session:
        item = session.get(WatchlistItem, item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item não encontrado.")
        item.target_price = body.target_price
        return {"id": item.id, "target_price": item.target_price}


@router.delete("/watchlist/{item_id}", status_code=204)
def watchlist_remove(item_id: int) -> None:
    with db.session() as session:
        item = session.get(WatchlistItem, item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item não encontrado.")
        session.delete(item)


# ── Comparação ──────────────────────────────────────────────────────────

def _parse_tickers(tickers: str) -> List[str]:
    out = list(dict.fromkeys(_norm(t) for t in tickers.split(",") if t.strip()))
    if not 2 <= len(out) <= 5:
        raise HTTPException(status_code=422, detail="Informe de 2 a 5 tickers.")
    return out


def _compare_item(ticker: str, period: str) -> Dict[str, Any]:
    agent = financial_agent()
    try:
        quote = agent.get_quote(ticker)
    except StockCollectorError as e:
        return {"ticker": ticker, "error": str(e)}
    fund = _safe(agent.get_fundamentals, ticker)
    points = _safe(_history_points, ticker, period) or []
    base = points[0]["close"] if points else None
    series = [{"date": p["date"], "value": p["close"] / base * 100} for p in points] if base else []
    return {
        "ticker": quote.ticker,
        "quote": quote.to_dict(),
        "fundamentals": fund.to_dict() if fund else None,
        "series": series,
        "error": None,
    }


@router.get("/compare")
def compare(tickers: str, period: str = "6mo") -> List[Dict[str, Any]]:
    """Cotação, fundamentos e desempenho relativo (base 100) de 2 a 5 ativos."""
    if period not in PERIODS:
        raise HTTPException(status_code=422, detail="Período inválido.")
    names = _parse_tickers(tickers)
    with ThreadPoolExecutor(max_workers=len(names)) as pool:
        return list(pool.map(lambda t: _compare_item(t, period), names))


@router.get("/compare/analysis")
def compare_analysis(tickers: str):
    """Comparação dos ativos pela IA, em streaming."""
    agent = financial_agent()
    require_llm(agent.llm)
    names = _parse_tickers(tickers)
    quotes, funds = [], []
    for t in names:
        try:
            quotes.append(agent.get_quote(t))
        except StockCollectorError as e:
            raise HTTPException(status_code=404, detail=str(e))
        funds.append(_safe(agent.get_fundamentals, t))
    prompt = agent.build_comparison_prompt(quotes, funds)
    return stream_text(
        lambda: agent.llm.generate_stream(prompt, system_prompt=FINANCIAL_ANALYSIS_SYSTEM_PROMPT)
    )
