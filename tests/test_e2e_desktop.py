"""Testes ponta a ponta do app desktop: a API real num processo à parte, clicada num navegador.

Rodam com dados falsos (STONKS_DATA_DIR numa pasta temporária) e sem internet nem IA:
as respostas da IA são simuladas no navegador. São pulados se o Playwright ou um
navegador não estiverem disponíveis. Navegador: Chromium do Playwright
(`playwright install chromium`) ou, no Windows, o Edge já instalado.
"""

import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.request
from datetime import date, timedelta
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
sync_api = pytest.importorskip("playwright.sync_api")

REPO = Path(__file__).resolve().parent.parent
VIEWS = ["inicio", "ativos", "watchlist", "comparar", "transacoes", "orcamento",
         "carteira", "contas", "metas", "alertas", "assistente", "ajustes"]


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def base_url(tmp_path_factory):
    port = _free_port()
    env = {**os.environ, "STONKS_DATA_DIR": str(tmp_path_factory.mktemp("dados")), "PYTHONIOENCODING": "utf-8",
           # Exportações iriam para a pasta Downloads de quem roda os testes
           "USERPROFILE": str(tmp_path_factory.mktemp("home")), "HOME": str(tmp_path_factory.mktemp("home2"))}
    env.pop("STONKS_API_TOKEN", None)
    log = open(tmp_path_factory.mktemp("log") / "server.log", "w")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "desktop.api:app", "--port", str(port)],
        cwd=REPO, env=env, stdout=log, stderr=subprocess.STDOUT,
    )
    url = f"http://127.0.0.1:{port}"
    try:
        for _ in range(120):
            try:
                urllib.request.urlopen(url + "/api/boot", timeout=1)
                break
            except OSError:
                time.sleep(0.25)
        else:
            pytest.fail("A API não subiu a tempo.")
        yield url
    finally:
        proc.terminate()
        proc.wait(timeout=10)
        log.close()


def call(base_url, method, path, body=None):
    req = urllib.request.Request(
        base_url + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        text = r.read().decode()
        return json.loads(text) if text else None


@pytest.fixture(scope="module")
def app_browser():
    with sync_api.sync_playwright() as p:
        channel = os.environ.get("STONKS_E2E_CHANNEL")
        tries = [channel] if channel else [None, "msedge"]
        for ch in tries:
            try:
                b = p.chromium.launch(channel=ch) if ch else p.chromium.launch()
                break
            except Exception:
                continue
        else:
            pytest.skip("Nenhum navegador para o Playwright (rode `playwright install chromium`).")
        yield b
        b.close()


@pytest.fixture
def page(app_browser, base_url):
    pg = app_browser.new_page(viewport={"width": 1366, "height": 860})
    pg.errors = []
    pg.on("pageerror", lambda e: pg.errors.append(str(e)))
    pg.goto(base_url + "/#inicio")
    pg.wait_for_selector("#view section")
    yield pg
    pg.close()


def go(page, view):
    page.click(f'.nav-item[data-view="{view}"]')
    page.wait_for_selector(f'.nav-item[data-view="{view}"][aria-current="page"]')
    page.wait_for_load_state("networkidle")


def test_every_screen_opens(page):
    for view in VIEWS:
        go(page, view)
        assert not page.locator("#view .empty", has_text="Erro ao abrir a tela").count(), view
    assert page.errors == []


def test_floating_chat_shares_the_conversation(page):
    page.route("**/api/chat", lambda r: r.fulfill(
        status=200, content_type="text/plain; charset=utf-8", body="**Reserva** é dinheiro para emergências."))
    page.click("#chat-open")
    assert page.locator("#chat-drawer").is_visible()
    page.fill("#chat-drawer textarea", "O que é reserva?")
    page.keyboard.press("Enter")
    page.wait_for_selector("#chat-drawer .msg.assistant strong")

    page.keyboard.press("Escape")
    assert page.locator("#chat-drawer").is_hidden()
    go(page, "assistente")
    assert page.locator("#view .msg").count() == 2
    assert page.errors == []


def test_hide_values_masks_money(page, base_url):
    call(base_url, "POST", "/api/transactions", {"description": "Salário", "amount": 5000, "type": "income"})
    page.reload()
    page.wait_for_selector("#kpis .kpi-value")
    page.click("#hide-toggle")
    page.wait_for_selector("#kpis .kpi-value")
    page.wait_for_load_state("networkidle")
    assert not re.findall(r"R\$\s?[\d.]+,\d\d", page.locator("#view").inner_text())
    page.click("#hide-toggle")  # devolve o estado para os outros testes
    page.wait_for_load_state("networkidle")


def test_scheduled_expense_is_not_spent_yet(page, base_url):
    today = date.today()
    if (today + timedelta(days=1)).month != today.month:
        pytest.skip("último dia do mês")
    call(base_url, "POST", "/api/transactions", {
        "description": "Academia", "amount": 99.9, "date": (today + timedelta(days=1)).isoformat(),
        "recurring_frequency": "monthly",
    })
    page.reload()
    page.locator("#kpis", has_text="agendado").wait_for()
    assert "R$ 99,90 agendado" in page.locator("#kpis").inner_text().replace(" ", " ")


def test_add_transaction_through_the_form(page):
    go(page, "transacoes")
    page.click("#add-btn")
    page.fill("dialog input[name=description]", "Padaria do bairro")
    page.fill("dialog input[name=amount]", "12.50")
    page.locator("dialog button[type=submit]").click()
    page.wait_for_selector("#tx-list td:has-text('Padaria do bairro')")
    assert page.locator(".toast", has_text="Transação adicionada").count()


def test_organize_with_ai_button(page):
    calls = {"post": 0}

    def fake(route):
        if route.request.method == "GET":
            return route.fulfill(json={"merchants": 3, "transactions": 4})
        calls["post"] += 1
        left = 3 - 2 * calls["post"]
        return route.fulfill(json={"asked": 2 if left >= 0 else 1, "categorized": 1, "transactions": 2,
                                   "remaining": max(left, 0)})

    page.route("**/api/categorize-ai", fake)
    go(page, "transacoes")
    page.click(".ai-sort button")
    page.wait_for_selector(".toast:has-text('A IA organizou')")
    assert calls["post"] == 2  # chamou até acabar


def test_pin_lock_and_unlock(page, base_url):
    call(base_url, "PUT", "/api/lock/pin", {"new_pin": "1234"})
    try:
        page.reload()
        page.wait_for_selector("#lock-now", state="visible")
        page.click("#lock-now")
        page.wait_for_selector("#lock-screen", state="visible")
        assert page.locator("#view").inner_text() == ""  # nada de dados atrás do bloqueio

        page.fill("#lock-pin", "0000")
        page.click("#lock-form button")
        page.wait_for_selector("#lock-error:has-text('PIN incorreto')")

        page.fill("#lock-pin", "1234")
        page.click("#lock-form button")
        page.wait_for_selector("#lock-screen", state="hidden")
        page.wait_for_selector("#view section")
    finally:
        call(base_url, "PUT", "/api/lock/pin", {"new_pin": "", "current_pin": "1234"})


def test_import_b3_statement_into_portfolio(page, tmp_path):
    import pandas as pd

    path = tmp_path / "negociacao-2025.xlsx"
    pd.DataFrame(
        [["02/01/2025", "Compra", "Mercado à Vista", "-", "XP", "PETR4", 100, 30, 3000],
         ["03/01/2025", "Compra", "Mercado Fracionário", "-", "XP", "ITSA4F", 7, 10, 70]],
        columns=["Data do Negócio", "Tipo de Movimentação", "Mercado", "Prazo/Vencimento", "Instituição",
                 "Código de Negociação", "Quantidade", "Preço", "Valor"],
    ).to_excel(path, index=False)

    go(page, "carteira")
    page.set_input_files("#b3-input", str(path))
    page.wait_for_selector(".toast:has-text('2 operações importadas do extrato de Negociação')")
    page.wait_for_selector("#pf-positions td:has-text('ITSA4')", timeout=60000)
    assert page.locator("#pf-ops tbody tr").count() == 2
    assert page.errors == []


def test_export_transactions_to_excel(page):
    go(page, "transacoes")
    page.click("#export-btn")
    page.locator("dialog.form-dialog button[type=submit]").click()
    page.wait_for_selector("dialog.form-dialog h2:has-text('Planilha salva')")
    assert ".xlsx foi salva em" in page.locator("dialog.form-dialog").inner_text()
    page.click("dialog.form-dialog button[value=cancel]")
    assert page.errors == []
