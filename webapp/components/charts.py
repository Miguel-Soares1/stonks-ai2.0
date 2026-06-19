"""
Gráficos Plotly reutilizáveis para a UI web.
"""

from typing import Any, Dict, List

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


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
