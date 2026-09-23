"""Tabela de preços por modelo, em USD por milhão de tokens.

Mantida aqui, simples e explícita, em vez de embutida num proxy de terceiro —
ajustar preço ou adicionar modelo é editar um dicionário."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelPrice:
    input_per_million: float
    output_per_million: float


PRICES: dict[str, ModelPrice] = {
    "claude-opus-5-5": ModelPrice(input_per_million=15.0, output_per_million=75.0),
    "claude-sonnet-5": ModelPrice(input_per_million=3.0, output_per_million=15.0),
    "claude-haiku-4-5-20251001": ModelPrice(input_per_million=0.8, output_per_million=4.0),
    "fake-model": ModelPrice(input_per_million=0.0, output_per_million=0.0),
}

DEFAULT_PRICE = ModelPrice(input_per_million=3.0, output_per_million=15.0)


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    price = PRICES.get(model, DEFAULT_PRICE)
    return (
        input_tokens * price.input_per_million / 1_000_000
        + output_tokens * price.output_per_million / 1_000_000
    )
