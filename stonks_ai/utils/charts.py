"""
Gráficos no terminal usando plotext.

Gera gráficos de linha e candlestick para visualização de preços de ações
diretamente no terminal.
"""

from typing import Any, Dict, List, Optional

from stonks_ai.config import config


class TerminalChart:
    """Gera gráficos para exibição no terminal."""

    def __init__(self, width: Optional[int] = None, height: Optional[int] = None):
        self.width = width or config.get("ui", "chart_width", default=60)
        self.height = height or config.get("ui", "chart_height", default=15)

    def line_chart(
        self,
        data: List[Dict[str, Any]],
        title: str = "",
        y_label: str = "Preço",
        x_key: str = "date",
        y_key: str = "close",
    ) -> str:
        """
        Gera gráfico de linha no terminal.

        Args:
            data: Lista de dicionários com dados históricos.
            title: Título do gráfico.
            y_label: Rótulo do eixo Y.
            x_key: Chave para o eixo X (datas).
            y_key: Chave para o eixo Y (preços).

        Returns:
            str: Representação textual do gráfico.
        """
        try:
            import plotext as plt

            plt.clear_figure()
            plt.theme("dark")

            dates = [self._format_date(d.get(x_key, "")) for d in data]
            values = [d.get(y_key, 0) for d in data]

            if not values:
                return "[Dados insuficientes para gerar gráfico]"

            plt.plot(dates, values, label=f"{title}")
            plt.title(f" {title} ", color="cyan")
            plt.xlabel("Data")
            plt.ylabel(y_label)

            plt.plotsize(self.width, self.height)

            # Ajusta número de ticks no eixo X
            if len(dates) > 10:
                plt.xticks(interval=max(1, len(dates) // 8))

            return plt.build()

        except ImportError:
            return "[plotext não instalado. Execute: pip install plotext]"
        except Exception as e:
            return f"[Erro ao gerar gráfico: {e}]"

    def comparison_chart(
        self,
        datasets: Dict[str, List[Dict[str, Any]]],
        title: str = "Comparação",
        x_key: str = "date",
        y_key: str = "close",
    ) -> str:
        """
        Gera gráfico de comparação entre múltiplos ativos.

        Args:
            datasets: Dict {nome_ativo: lista_de_dados}
            title: Título do gráfico.
            x_key: Chave para datas.
            y_key: Chave para valores.

        Returns:
            str: Gráfico comparativo.
        """
        try:
            import plotext as plt

            plt.clear_figure()
            plt.theme("dark")

            colors = ["blue", "green", "yellow", "red", "magenta", "cyan"]

            for i, (name, data) in enumerate(datasets.items()):
                dates = [self._format_date(d.get(x_key, "")) for d in data]
                # Normaliza valores para percentual (base 100 no primeiro dia)
                values = [d.get(y_key, 0) for d in data]
                if values and values[0] != 0:
                    values = [(v / values[0] - 1) * 100 for v in values]

                color = colors[i % len(colors)]
                plt.plot(dates, values, label=f"{name}", color=color)

            plt.title(f" {title} (Base 100%) ", color="cyan")
            plt.xlabel("Data")
            plt.ylabel("Variação %")

            plt.plotsize(self.width, self.height)

            return plt.build()

        except ImportError:
            return "[plotext não instalado]"
        except Exception as e:
            return f"[Erro ao gerar gráfico comparativo: {e}]"

    @staticmethod
    def _format_date(date_str: str) -> str:
        """Formata data para exibição compacta no gráfico."""
        if not date_str:
            return ""
        try:
            # Formato ISO -> DD/MM
            parts = date_str[:10].split("-")
            if len(parts) == 3:
                return f"{parts[2]}/{parts[1]}"
            return date_str[:10]
        except Exception:
            return date_str[:10]


def render_line_chart(
    data: List[Dict[str, Any]],
    title: str = "",
    **kwargs,
) -> str:
    """Função de conveniência para gerar gráfico de linha."""
    chart = TerminalChart()
    return chart.line_chart(data, title=title, **kwargs)
