"""
Gráficos Plotly reutilizáveis para a UI web.
"""

from typing import Any, Dict, List

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from stonks_ai.utils.formatters import format_currency


def build_price_chart(
    data: List[Dict[str, Any]],
    ticker: str,
    title: str = "",
) -> go.Figure:
    """Constrói gráfico de velas (candlestick) com Plotly."""
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.7, 0.3],
    )

    # Candlestick
    fig.add_trace(
        go.Candlestick(
            x=df["date"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name=ticker,
            increasing_line_color="#00ff88",
            decreasing_line_color="#ff4444",
        ),
        row=1,
        col=1,
    )

    # Volume
    colors = [
        "#00ff88" if df["close"].iloc[i] >= df["open"].iloc[i] else "#ff4444"
        for i in range(len(df))
    ]
    fig.add_trace(
        go.Bar(
            x=df["date"],
            y=df["volume"],
            name="Volume",
            marker_color=colors,
            opacity=0.6,
        ),
        row=2,
        col=1,
    )

    fig.update_layout(
        title=title or f"{ticker} - Preço Histórico",
        xaxis_title="Data",
        yaxis_title="Preço",
        template="plotly_dark",
        hovermode="x unified",
        margin=dict(l=40, r=40, t=40, b=40),
        height=600,
        showlegend=False,
        xaxis_rangeslider_visible=False,
    )

    fig.update_yaxes(title_text="Preço", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)

    return fig


def build_comparison_chart(
    datasets: Dict[str, pd.DataFrame],
    title: str = "Comparação (Base 100)",
) -> go.Figure:
    """Constrói gráfico de comparação normalizado (base 100)."""
    fig = go.Figure()

    colors = [
        "#00ff88", "#00cc6a", "#66ffaa", "#009955",
        "#33ee77", "#00bb55", "#88ffbb", "#00dd66",
    ]

    for i, (name, df) in enumerate(datasets.items()):
        if df.empty:
            continue
        base = df["close"].iloc[0]
        if base == 0:
            continue
        normalized = (df["close"] / base) * 100
        color = colors[i % len(colors)]
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=normalized,
                mode="lines",
                name=name,
                line=dict(width=2, color=color),
            )
        )

    fig.update_layout(
        title=title,
        xaxis_title="Data",
        yaxis_title="Variação % (Base 100)",
        template="plotly_dark",
        hovermode="x unified",
        margin=dict(l=40, r=40, t=40, b=40),
        height=500,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
    )

    fig.add_hline(y=100, line_dash="dash", line_color="gray", opacity=0.5)

    return fig


def build_category_pie_chart(
    categories: List[Dict[str, Any]],
    title: str = "Gastos por Categoria",
) -> go.Figure:
    """Constrói gráfico de pizza com gastos por categoria.

    Args:
        categories: Lista de dicts com 'name', 'amount', 'percent'.
        title: Título do gráfico.
    """
    if not categories:
        fig = go.Figure()
        fig.add_annotation(
            text="Sem dados de categorias",
            showarrow=False,
            font=dict(size=16, color="#888"),
        )
        fig.update_layout(template="plotly_dark", height=350)
        return fig

    labels = [c["name"] for c in categories]
    values = [c["amount"] for c in categories]
    percentages = [f"{c['percent']:.1f}%" for c in categories]
    hover_texts = [
        f"{c['name']}<br>{format_currency(c['amount'])}<br>{c['percent']:.1f}%"
        for c in categories
    ]

    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.45,
            textinfo="label+percent",
            hovertext=hover_texts,
            hoverinfo="text",
            marker=dict(
                colors=[
                    "#FF6B35", "#004E89", "#1A659E", "#FF006E",
                    "#00A896", "#8338EC", "#3A86FF", "#06D6A0",
                    "#118AB2", "#0D3B66", "#6C757D",
                ],
                line=dict(color="#1a1a2e", width=1),
            ),
            sort=True,
            direction="clockwise",
        )
    )

    fig.update_layout(
        title=title,
        template="plotly_dark",
        height=380,
        margin=dict(l=20, r=20, t=40, b=20),
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.02,
            font=dict(size=11),
        ),
    )

    return fig


def build_monthly_bars_chart(
    monthly_summaries: List[Dict[str, Any]],
    title: str = "Receitas vs Despesas",
) -> go.Figure:
    """Constrói gráfico de barras com receitas e despesas dos últimos meses.

    Args:
        monthly_summaries: Lista de resumos mensais (de get_multi_month_summary).
        title: Título do gráfico.
    """
    if not monthly_summaries:
        fig = go.Figure()
        fig.add_annotation(
            text="Sem dados históricos",
            showarrow=False,
            font=dict(size=16, color="#888"),
        )
        fig.update_layout(template="plotly_dark", height=350)
        return fig

    months = [
        f"{s['month']:02d}/{s['year']}" for s in monthly_summaries
    ]
    incomes = [s["total_income"] for s in monthly_summaries]
    expenses = [s["total_expense"] for s in monthly_summaries]
    balances = [s["balance"] for s in monthly_summaries]

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=months,
            y=incomes,
            name="Receitas",
            marker_color="#06D6A0",
            text=[f"R$ {v:,.0f}" for v in incomes],
            textposition="outside",
            textfont=dict(size=10, color="#06D6A0"),
        )
    )

    fig.add_trace(
        go.Bar(
            x=months,
            y=expenses,
            name="Despesas",
            marker_color="#FF006E",
            text=[f"R$ {v:,.0f}" for v in expenses],
            textposition="outside",
            textfont=dict(size=10, color="#FF006E"),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=months,
            y=balances,
            name="Saldo",
            mode="lines+markers",
            line=dict(color="#FFD166", width=3),
            marker=dict(size=8, color="#FFD166"),
            yaxis="y2",
        )
    )

    fig.update_layout(
        title=title,
        template="plotly_dark",
        height=380,
        margin=dict(l=20, r=20, t=40, b=20),
        hovermode="x unified",
        barmode="group",
        bargap=0.25,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=11),
        ),
        yaxis=dict(title="Valor (R$)", gridcolor="#333"),
        yaxis2=dict(
            title="Saldo (R$)",
            overlaying="y",
            side="right",
            showgrid=False,
        ),
    )

    return fig


def build_balance_line_chart(
    balance_history: List[Dict[str, Any]],
    title: str = "Evolução do Saldo",
) -> go.Figure:
    """Constrói gráfico de linha da evolução do saldo acumulado.

    Args:
        balance_history: Lista de dicts com 'date' e 'balance'.
        title: Título do gráfico.
    """
    if not balance_history:
        fig = go.Figure()
        fig.add_annotation(
            text="Sem dados de saldo",
            showarrow=False,
            font=dict(size=16, color="#888"),
        )
        fig.update_layout(template="plotly_dark", height=350)
        return fig

    dates = [h["date"] for h in balance_history]
    balances = [h["balance"] for h in balance_history]

    # Colorir área: verde se positivo, vermelho se negativo
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=dates,
            y=balances,
            mode="lines",
            name="Saldo",
            line=dict(color="#06D6A0", width=2),
            fill="tozeroy",
            fillcolor="rgba(6, 214, 160, 0.15)",
        )
    )

    # Linha zero
    fig.add_hline(
        y=0,
        line_dash="dash",
        line_color="#666",
        opacity=0.5,
        annotation_text="R$ 0",
        annotation_position="bottom right",
    )

    fig.update_layout(
        title=title,
        template="plotly_dark",
        height=350,
        margin=dict(l=20, r=20, t=40, b=20),
        hovermode="x unified",
        showlegend=False,
        yaxis=dict(title="Saldo (R$)", gridcolor="#333"),
        xaxis=dict(title="Data", gridcolor="#333"),
    )

    return fig
