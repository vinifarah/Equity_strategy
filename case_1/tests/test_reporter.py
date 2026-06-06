"""Unit tests for src/reporter.py — no API calls required."""
from __future__ import annotations

from src.reporter import generate_report


class TestGenerateReport:
    def test_returns_string(self, sample_analysis):
        report = generate_report(sample_analysis)
        assert isinstance(report, str)
        assert len(report) > 0

    def test_contains_ticker_and_company(self, sample_analysis):
        report = generate_report(sample_analysis)
        assert "PETR4" in report
        assert "Petrobras" in report

    def test_contains_quarter(self, sample_analysis):
        report = generate_report(sample_analysis)
        assert "4T24" in report

    def test_contains_sentiment(self, sample_analysis):
        report = generate_report(sample_analysis)
        assert "CAUTIOUS" in report or "cautious" in report

    def test_contains_surprise_score(self, sample_analysis):
        report = generate_report(sample_analysis)
        assert "7/10" in report

    def test_word_count_within_limit(self, sample_analysis):
        report = generate_report(sample_analysis, max_words=400)
        words = report.split()
        # Allow a small buffer for the truncation suffix itself
        assert len(words) <= 420

    def test_truncation_suffix_when_too_long(self, sample_analysis):
        # Force truncation by setting a very small word limit
        report = generate_report(sample_analysis, max_words=10)
        assert "truncado" in report

    def test_no_self_critique_badge_when_absent(self, sample_analysis_no_critique):
        report = generate_report(sample_analysis_no_critique)
        assert "Self-critique" not in report

    def test_self_critique_badge_present(self, sample_analysis):
        report = generate_report(sample_analysis)
        assert "Self-critique" in report
        assert "8/10" in report

    def test_red_flags_section_present(self, sample_analysis):
        report = generate_report(sample_analysis)
        assert "Red Flag" in report

    def test_no_red_flags_section_when_empty(self, sample_analysis):
        sample_analysis.red_flags = []
        report = generate_report(sample_analysis)
        assert "Red Flag" not in report

    def test_only_high_significance_guidance_in_report(self, sample_analysis):
        # The fixture has one "high" item (Capex) and one "low" item (Lifting Cost)
        report = generate_report(sample_analysis)
        assert "Capex" in report
        # Low-significance items should not appear in the table
        assert "Lifting Cost" not in report

    def test_at_most_two_red_flags_shown(self, sample_analysis):
        from src.models import RedFlag
        # Add a third flag (low severity — should be cut by the top-2 logic)
        sample_analysis.red_flags.append(
            RedFlag(
                flag_type="vague_answer",
                speaker="CFO",
                excerpt="We will provide an update in future quarters.",
                analysis="Delay tactic.",
                severity="low",
            )
        )
        report = generate_report(sample_analysis)
        # Verify by flag labels (more robust than emoji counting, which appears in other sections)
        assert "Resposta vaga" not in report   # low-severity flag was cut
        assert "Evasão" in report              # first high-severity flag kept
        assert "Hesitação" in report           # second high-severity flag kept

    def test_top_3_questions_present(self, sample_analysis):
        report = generate_report(sample_analysis)
        assert "Gabriel Barra" in report
        assert "Regis Cardoso" in report
        assert "Bruno Amorim" in report
