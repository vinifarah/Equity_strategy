from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Optional

from .models import MarketReaction

try:
    import yfinance as yf
    _YFINANCE_OK = True
except ImportError:
    _YFINANCE_OK = False


def _parse_date(s: str) -> Optional[date]:
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass
    return None


def _b3_to_yf(ticker: str) -> str:
    t = ticker.upper().strip()
    return t if t.endswith(".SA") else t + ".SA"


def _pct(p1: Optional[float], p2: Optional[float]) -> Optional[float]:
    if p1 and p2 and p1 != 0:
        return round((p2 - p1) / p1 * 100, 2)
    return None


def _close_on(hist, target: date) -> Optional[float]:
    matching = [i for i in hist.index if i.date() == target]
    if not matching:
        return None
    return float(hist.loc[matching[0], "Close"])


def _interpret(alpha_d1: Optional[float], alpha_d5: Optional[float]) -> str:
    if alpha_d1 is None:
        return "Dados insuficientes para interpretação."
    parts = []
    if alpha_d1 >= 2:
        parts.append(f"Mercado reagiu positivamente na D+1 (alpha +{alpha_d1:.1f}% vs Ibovespa)")
    elif alpha_d1 <= -2:
        parts.append(f"Mercado reagiu negativamente na D+1 (alpha {alpha_d1:.1f}% vs Ibovespa)")
    else:
        parts.append(f"Reação neutra na D+1 (alpha {alpha_d1:+.1f}% vs Ibovespa)")
    if alpha_d5 is not None:
        if alpha_d5 * (alpha_d1 or 0) > 0 and abs(alpha_d5) >= 2:
            parts.append(f"movimento manteve-se até D+5 (alpha acumulado {alpha_d5:+.1f}%)")
        elif abs(alpha_d5) >= 2:
            parts.append(f"movimento reverteu parcialmente até D+5 (alpha acumulado {alpha_d5:+.1f}%)")
    return ". ".join(parts) + "."


def get_market_reaction(ticker: str, call_date_str: str) -> MarketReaction:
    """Fetch stock price reaction around the earnings call date via Yahoo Finance.

    Returns a MarketReaction with data_available=False if data cannot be fetched.
    """
    if not _YFINANCE_OK:
        return MarketReaction(
            call_date=call_date_str,
            data_available=False,
            interpretation="yfinance não instalado. Execute: pip install yfinance",
        )

    call_dt = _parse_date(call_date_str)
    if call_dt is None:
        return MarketReaction(
            call_date=call_date_str,
            data_available=False,
            interpretation="Data da call não reconhecida (esperado YYYY-MM-DD).",
        )

    try:
        yf_ticker = _b3_to_yf(ticker)
        start = (call_dt - timedelta(days=14)).isoformat()
        end = (call_dt + timedelta(days=20)).isoformat()

        stock_hist = yf.Ticker(yf_ticker).history(start=start, end=end)
        ibov_hist = yf.Ticker("^BVSP").history(start=start, end=end)

        if stock_hist.empty:
            return MarketReaction(
                call_date=call_date_str,
                data_available=False,
                interpretation=f"Sem dados de preço para {yf_ticker} no Yahoo Finance.",
            )

        stock_dates = sorted({i.date() for i in stock_hist.index})
        ibov_dates = sorted({i.date() for i in ibov_hist.index})

        pre = [d for d in stock_dates if d < call_dt]
        on_post = [d for d in stock_dates if d >= call_dt]

        if not pre or not on_post:
            return MarketReaction(
                call_date=call_date_str,
                data_available=False,
                interpretation="Janela de dados insuficiente ao redor da data da call.",
            )

        d_m1 = pre[-1]
        d_0 = on_post[0]
        future = [d for d in stock_dates if d > d_0]

        p_dm1 = _close_on(stock_hist, d_m1)
        p_d0 = _close_on(stock_hist, d_0)
        p_d1 = _close_on(stock_hist, future[0]) if len(future) >= 1 else None
        p_d5 = _close_on(stock_hist, future[4]) if len(future) >= 5 else None

        ibov_pre = [d for d in ibov_dates if d <= d_m1]
        ibov_future = [d for d in ibov_dates if d > d_0]
        ibov_dm1 = _close_on(ibov_hist, ibov_pre[-1]) if ibov_pre else None
        ibov_d1 = _close_on(ibov_hist, ibov_future[0]) if len(ibov_future) >= 1 else None
        ibov_d5 = _close_on(ibov_hist, ibov_future[4]) if len(ibov_future) >= 5 else None

        ret_d1 = _pct(p_dm1, p_d1)
        ret_d5 = _pct(p_dm1, p_d5)
        ibov_ret_d1 = _pct(ibov_dm1, ibov_d1)
        ibov_ret_d5 = _pct(ibov_dm1, ibov_d5)
        alpha_d1 = round(ret_d1 - ibov_ret_d1, 2) if ret_d1 is not None and ibov_ret_d1 is not None else None
        alpha_d5 = round(ret_d5 - ibov_ret_d5, 2) if ret_d5 is not None and ibov_ret_d5 is not None else None

        return MarketReaction(
            call_date=d_0.isoformat(),
            data_available=True,
            price_d_minus_1=p_dm1,
            price_d_close=p_d0,
            price_d_plus_1=p_d1,
            price_d_plus_5=p_d5,
            return_d1_pct=ret_d1,
            return_d5_pct=ret_d5,
            ibov_return_d1_pct=ibov_ret_d1,
            ibov_return_d5_pct=ibov_ret_d5,
            alpha_d1_pct=alpha_d1,
            alpha_d5_pct=alpha_d5,
            interpretation=_interpret(alpha_d1, alpha_d5),
        )

    except Exception as e:
        return MarketReaction(
            call_date=call_date_str,
            data_available=False,
            interpretation=f"Erro ao buscar dados de mercado: {e}",
        )
