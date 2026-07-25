"""
test_app.py
-------------
Smoke tests for app.py using Streamlit's official AppTest framework
(streamlit.testing.v1). This is the authoritative way to verify a
Streamlit app runs without exceptions -- checking the rendered HTML or
the server health endpoint only proves the server booted, not that the
script logic (data loading, pandas transforms, RFM segmentation, chart
construction) executed cleanly. AppTest actually runs the script and
inspects the resulting widget tree.

Run with: python -m pytest test_app.py -v
"""
import pytest
from streamlit.testing.v1 import AppTest


@pytest.fixture
def app():
    at = AppTest.from_file("app.py")
    at.run()
    return at


def test_app_runs_without_exceptions(app):
    assert not app.exception, f"App raised exception(s): {app.exception}"


def test_kpi_metrics_render(app):
    assert len(app.metric) == 4
    labels = {m.label for m in app.metric}
    assert labels == {"Total Revenue", "Orders", "Unique Customers", "Avg Order Value"}


def test_sidebar_filters_present(app):
    assert len(app.multiselect) == 2  # state + category
    assert len(app.date_input) == 1


def test_state_filter_changes_kpis(app):
    """The whole point of an interactive dashboard is that filters
    actually filter. This test proves it, rather than just checking
    that the widget exists."""
    state_widget = app.multiselect[0]  # "Customer state"
    unfiltered_revenue = next(m.value for m in app.metric if m.label == "Total Revenue")

    state_widget.set_value([state_widget.options[0]])
    app.run()
    assert not app.exception

    filtered_revenue = next(m.value for m in app.metric if m.label == "Total Revenue")
    assert filtered_revenue != unfiltered_revenue, (
        "Filtering to a single state should change total revenue -- "
        "if it didn't, the filter isn't actually wired to the data."
    )


def test_category_filter_changes_kpis(app):
    category_widget = app.multiselect[1]  # "Product category"
    unfiltered_orders = next(m.value for m in app.metric if m.label == "Orders")

    category_widget.set_value([category_widget.options[0]])
    app.run()
    assert not app.exception

    filtered_orders = next(m.value for m in app.metric if m.label == "Orders")
    assert filtered_orders != unfiltered_orders


def test_empty_filter_shows_warning_not_crash(app):
    """Selecting zero states should show a graceful warning, not crash
    with an unhandled exception (e.g. division by zero in AOV calc)."""
    state_widget = app.multiselect[0]
    state_widget.set_value([])
    app.run()
    assert not app.exception
    assert len(app.warning) > 0
