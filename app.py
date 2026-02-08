"""
Wisconsin BRRTS Site Browser

FastHTML web UI for browsing Wisconsin DNR BRRTS scraped data.
Mirrors Oregon ECSI / MILO CRM patterns: FastHTML + MonsterUI + HTMX + SQLite.

Usage:
    python app.py
    # Then open http://localhost:5010
"""
from fasthtml.common import *
from monsterui.all import *
import db

# ---------------------------------------------------------------------------
# App initialization
# ---------------------------------------------------------------------------

app, rt = fast_app(
    live=True,
    hdrs=(
        Theme.blue.headers(),
        Style("""
/* ---- Layout ---- */
:root {
    --sidebar-width: 220px;
    --sidebar-bg: #1e293b;
    --sidebar-text: #94a3b8;
    --sidebar-active: #3b82f6;
    --sidebar-hover: #334155;
}

* { box-sizing: border-box; }

body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f1f5f9; color: #1e293b; }

.app-layout { display: flex; min-height: 100vh; }

.sidebar {
    position: fixed; top: 0; left: 0; bottom: 0;
    width: var(--sidebar-width); background: var(--sidebar-bg);
    display: flex; flex-direction: column; z-index: 100;
}
.sidebar-brand { padding: 20px 16px 16px; border-bottom: 1px solid #334155; }
.sidebar-brand h1 { margin: 0; font-size: 18px; color: #f8fafc; font-weight: 700; letter-spacing: -0.5px; }
.sidebar-brand span { font-size: 11px; color: var(--sidebar-text); }
.sidebar-nav { padding: 12px 8px; flex: 1; }
.sidebar-nav a {
    display: flex; align-items: center; gap: 10px;
    padding: 10px 12px; border-radius: 8px; color: var(--sidebar-text);
    text-decoration: none; font-size: 14px; font-weight: 500;
    transition: all 0.15s;
}
.sidebar-nav a:hover { background: var(--sidebar-hover); color: #e2e8f0; }
.sidebar-nav a.active { background: var(--sidebar-active); color: #ffffff; }

.main-content {
    margin-left: var(--sidebar-width); flex: 1;
    padding: 24px 32px; max-width: 1400px;
}

/* ---- Page header ---- */
.page-header {
    display: flex; align-items: center; gap: 16px;
    margin-bottom: 20px;
}
.page-header h1 { margin: 0; font-size: 24px; font-weight: 700; }
.page-header .count { font-size: 14px; color: #64748b; background: #e2e8f0; padding: 2px 10px; border-radius: 9999px; }

/* ---- Cards ---- */
.card {
    background: #ffffff; border-radius: 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06); margin-bottom: 20px;
    overflow: hidden;
}
.card-header {
    padding: 16px 20px; border-bottom: 1px solid #e2e8f0;
    font-size: 15px; font-weight: 600;
}
.card-header h2 { margin: 0; font-size: 15px; font-weight: 600; }
.card-body { padding: 20px; }

/* ---- KPI cards ---- */
.kpi-grid {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 16px; margin-bottom: 24px;
}
.kpi-card {
    background: #fff; border-radius: 12px; padding: 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    text-align: center;
}
.kpi-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
a.kpi-link { text-decoration: none; color: inherit; }
.kpi-value { font-size: 32px; font-weight: 700; color: #1e293b; }
.kpi-label { font-size: 13px; color: #64748b; margin-top: 4px; text-transform: uppercase; letter-spacing: 0.5px; }

/* ---- Badges ---- */
.badge {
    display: inline-block; padding: 2px 10px; border-radius: 9999px;
    font-size: 12px; font-weight: 500; white-space: nowrap;
}
.badge-blue { background: #dbeafe; color: #1e40af; }
.badge-green { background: #dcfce7; color: #166534; }
.badge-yellow { background: #fef9c3; color: #854d0e; }
.badge-red { background: #fee2e2; color: #991b1b; }
.badge-gray { background: #f1f5f9; color: #475569; }
.badge-purple { background: #f3e8ff; color: #6b21a8; }
.badge-orange { background: #ffedd5; color: #9a3412; }
.badge-lg { font-size: 14px; padding: 4px 14px; }

/* ---- Filter row ---- */
.filter-bar {
    display: flex; justify-content: flex-start; padding: 12px 20px 0;
}
.clear-filters-btn {
    padding: 5px 12px; font-size: 12px; font-weight: 500; color: #64748b;
    background: none; border: 1px solid #d1d5db; border-radius: 6px;
    cursor: pointer; text-decoration: none;
}
.clear-filters-btn:hover { background: #f1f5f9; color: #1e293b; }
.filter-row {
    display: flex; flex-wrap: wrap; gap: 10px; padding: 16px 20px;
    border-bottom: 1px solid #e2e8f0; align-items: center;
}
.filter-row select, .filter-row input[type="text"] {
    padding: 7px 12px; border: 1px solid #d1d5db; border-radius: 8px;
    font-size: 13px; background: #fff; color: #1e293b; flex: 1; min-width: 120px;
}
.filter-row input[type="text"] { min-width: 180px; flex: 2; }
.filter-row select:focus, .filter-row input:focus { outline: none; border-color: #3b82f6; box-shadow: 0 0 0 2px rgba(59,130,246,0.2); }

/* ---- Data table ---- */
.data-table { width: 100%; border-collapse: collapse; }
.data-table th {
    padding: 10px 16px; text-align: left; font-size: 12px;
    font-weight: 600; color: #64748b; text-transform: uppercase;
    letter-spacing: 0.5px; border-bottom: 2px solid #e2e8f0;
    white-space: nowrap;
}
.data-table th a { color: #64748b; text-decoration: none; }
.data-table th a:hover { color: #1e293b; }
.data-table th.sorted a { color: #3b82f6; }
.data-table td { padding: 10px 16px; font-size: 13px; border-bottom: 1px solid #f1f5f9; }
.data-table tr:hover td { background: #f8fafc; }
.data-table td a { color: #2563eb; text-decoration: none; font-weight: 500; }
.data-table td a:hover { text-decoration: underline; }

/* ---- Pagination ---- */
.pagination {
    display: flex; align-items: center; justify-content: space-between;
    padding: 12px 20px; border-top: 1px solid #e2e8f0;
}
.pagination .info { font-size: 13px; color: #64748b; }
.pagination .controls { display: flex; gap: 8px; }
.pagination button, .pagination .btn {
    padding: 6px 14px; border: 1px solid #d1d5db; border-radius: 6px;
    font-size: 13px; background: #fff; color: #374151; cursor: pointer;
}
.pagination button:hover:not(:disabled) { background: #f1f5f9; }
.pagination button:disabled { opacity: 0.4; cursor: default; }

/* ---- Detail view ---- */
.detail-header {
    display: flex; align-items: flex-start; justify-content: space-between;
    margin-bottom: 24px; gap: 16px;
}
.detail-title { margin: 0; font-size: 22px; font-weight: 700; }
.detail-subtitle { font-size: 14px; color: #64748b; margin-top: 4px; }
.detail-badges { display: flex; gap: 8px; flex-wrap: wrap; }

.detail-grid {
    display: grid; grid-template-columns: 1fr 1fr; gap: 0;
}
.detail-item {
    padding: 12px 20px; border-bottom: 1px solid #f1f5f9;
}
.detail-item .label {
    font-size: 11px; font-weight: 600; color: #64748b;
    text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 2px;
}
.detail-item .value { font-size: 14px; color: #1e293b; }

/* ---- Substances list ---- */
.substance-tag {
    display: inline-block; padding: 4px 12px; margin: 3px;
    background: #fef3c7; color: #92400e; border-radius: 6px;
    font-size: 12px; font-weight: 500;
}
.medium-tag {
    display: inline-block; padding: 4px 12px; margin: 3px;
    background: #e0e7ff; color: #3730a3; border-radius: 6px;
    font-size: 12px; font-weight: 500;
}

/* ---- Actions timeline ---- */
.action-item {
    padding: 12px 0; border-bottom: 1px solid #f1f5f9;
}
.action-item:last-child { border-bottom: none; }
.action-date { font-size: 12px; font-weight: 600; color: #3b82f6; font-family: monospace; margin-bottom: 2px; }
.action-name { font-size: 14px; font-weight: 600; color: #1e293b; }
.action-desc { font-size: 13px; color: #64748b; margin-top: 2px; }

/* ---- Notice ---- */
.notice { padding: 16px 20px; border-radius: 8px; font-size: 14px; margin-bottom: 16px; }
.notice-info { background: #eff6ff; color: #1e40af; border: 1px solid #bfdbfe; }
.notice-warning { background: #fffbeb; color: #92400e; border: 1px solid #fde68a; }

/* ---- Empty state ---- */
.empty-state { text-align: center; padding: 60px 20px; color: #64748b; }
.empty-state h2 { font-size: 18px; color: #475569; margin-bottom: 8px; }
.empty-state p { font-size: 14px; margin: 0; }

/* ---- Breakdown rows ---- */
.breakdown-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 10px 20px; border-bottom: 1px solid #f1f5f9;
}
.breakdown-row:last-child { border-bottom: none; }
.breakdown-row a { color: #2563eb; text-decoration: none; font-size: 14px; }
.breakdown-row a:hover { text-decoration: underline; }
.breakdown-row span { font-size: 14px; font-weight: 600; color: #1e293b; }

/* ---- Back button ---- */
.back-btn {
    display: inline-flex; align-items: center; gap: 6px;
    color: #64748b; text-decoration: none; font-size: 13px;
    font-weight: 500; margin-bottom: 16px;
}
.back-btn:hover { color: #1e293b; }

/* ---- Scraped icon ---- */
.scraped-icon { font-size: 16px; }
.scraped-yes { color: #16a34a; }
.scraped-no { color: #d1d5db; }
.scraped-fail { color: #ef4444; }

/* ---- Document selection ---- */
.doc-checkbox { width: 18px; height: 18px; cursor: pointer; accent-color: #3b82f6; }
.doc-selected td { background: #eff6ff; }
.docs-header-count { font-weight: 400; color: #64748b; font-size: 14px; }

/* ---- Wisdom / qualification notes ---- */
.wisdom-textarea {
    width: 100%; min-height: 80px; padding: 12px; border: 1px solid #d1d5db;
    border-radius: 8px; font-size: 14px; font-family: inherit; line-height: 1.6;
    resize: vertical; color: #1e293b; background: #fff;
}
.wisdom-textarea:focus { outline: none; border-color: #3b82f6; box-shadow: 0 0 0 2px rgba(59,130,246,0.2); }
.wisdom-actions {
    display: flex; align-items: center; gap: 12px; margin-top: 8px;
}
.wisdom-save-btn {
    padding: 6px 16px; background: #3b82f6; color: #fff; border: none;
    border-radius: 6px; font-size: 13px; font-weight: 500; cursor: pointer;
}
.wisdom-save-btn:hover { background: #2563eb; }
.wisdom-save-status { font-size: 12px; color: #16a34a; font-weight: 500; }
.wisdom-timeline { padding: 0 20px 16px; }
.wisdom-note {
    padding: 12px 0; border-bottom: 1px solid #f1f5f9;
    font-size: 14px; line-height: 1.6; color: #334155;
}
.wisdom-note:last-child { border-bottom: none; }
.wisdom-note .wisdom-timestamp {
    font-size: 11px; color: #94a3b8; margin-bottom: 4px;
}
.wisdom-note .wisdom-text { white-space: pre-wrap; }

/* ---- HTMX loading ---- */
.htmx-indicator { display: none; }
.htmx-request .htmx-indicator { display: inline-block; }
.htmx-request.htmx-indicator { display: inline-block; }

/* ---- Responsive ---- */
@media (max-width: 768px) {
    .sidebar { display: none; }
    .main-content { margin-left: 0; padding: 16px; }
    .detail-grid { grid-template-columns: 1fr; }
    .filter-row { flex-direction: column; }
}
        """),
    ),
    pico=False,
)

db.init_db()

# ---------------------------------------------------------------------------
# Helper components
# ---------------------------------------------------------------------------

def sidebar(active: str = ''):
    nav_items = [
        ('/', 'Dashboard', 'bar-chart-2'),
        ('/sites', 'Sites', 'map-pin'),
    ]
    links = []
    for href, label, icon in nav_items:
        cls = 'active' if active == href else ''
        links.append(A(UkIcon(icon), Span(label), href=href, cls=cls))

    return Aside(
        Div(
            H1("Wisconsin DNR"),
            Span("BRRTS Site Browser"),
            cls="sidebar-brand",
        ),
        Nav(*links, cls="sidebar-nav"),
        cls="sidebar",
    )


def page_layout(content, active: str = '/'):
    return (
        Title("Wisconsin BRRTS Site Browser"),
        Div(
            sidebar(active),
            Main(content, cls="main-content"),
            cls="app-layout",
        ),
    )


def kpi_card(value, label, href=None):
    formatted = f"{value:,}" if isinstance(value, int) else str(value)
    card = Div(
        Div(formatted, cls="kpi-value"),
        Div(label, cls="kpi-label"),
        cls="kpi-card",
    )
    if href:
        return A(card, href=href, cls="kpi-link")
    return card


def badge(text, variant='gray'):
    return Span(text or '--', cls=f"badge badge-{variant}")


def type_variant(activity_type: str) -> str:
    if not activity_type:
        return 'gray'
    t = activity_type.lower()
    if t == 'erp':
        return 'blue'
    if t == 'lust':
        return 'purple'
    if t == 'spills':
        return 'orange'
    if t == 'nar':
        return 'green'
    return 'gray'


def status_variant(status: str) -> str:
    if not status:
        return 'gray'
    s = status.lower()
    if s == 'open':
        return 'yellow'
    if s == 'closed':
        return 'green'
    return 'gray'


def format_date(val):
    if not val:
        return '--'
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(val.replace('Z', '+00:00'))
        return dt.strftime('%b %d, %Y')
    except (ValueError, AttributeError):
        return str(val)[:10] if val else '--'


def format_value(val):
    if val is None or val == '':
        return '--'
    return str(val)


def empty_state(message: str, subtitle: str = ''):
    return Div(
        H2(message),
        P(subtitle) if subtitle else None,
        cls="empty-state",
    )


def sortable_header(label, column, current_sort, current_order, base_url, params, target="#table-content"):
    new_order = 'desc' if (current_sort == column and current_order == 'asc') else 'asc'
    indicator = ''
    cls = ''
    if current_sort == column:
        indicator = ' ↑' if current_order == 'asc' else ' ↓'
        cls = 'sorted'
    new_params = {**params, 'sort': column, 'order': new_order, 'page': 1}
    query_str = '&'.join(f"{k}={v}" for k, v in new_params.items() if v != '')
    url = f"{base_url}?{query_str}"
    return Th(
        A(f"{label}{indicator}", href="javascript:void(0)",
          hx_get=url, hx_target=target, hx_swap="innerHTML",
          style="cursor:pointer;"),
        cls=cls,
    )


def pagination_controls(page, total, per_page, base_url, params, target="#table-content"):
    total_pages = max(1, (total + per_page - 1) // per_page)
    start = min((page - 1) * per_page + 1, total)
    end = min(page * per_page, total)

    def page_url(p):
        new_params = {**params, 'page': p}
        query_str = '&'.join(f"{k}={v}" for k, v in new_params.items() if v != '')
        return f"{base_url}?{query_str}"

    return Div(
        Span(f"Showing {start}--{end} of {total:,}", cls="info") if total > 0 else Span("No results", cls="info"),
        Div(
            Button("Previous", disabled=(page <= 1),
                   hx_get=page_url(page - 1), hx_target=target, hx_swap="innerHTML") if page > 1 else
            Button("Previous", disabled=True),
            Button("Next", disabled=(page >= total_pages),
                   hx_get=page_url(page + 1), hx_target=target, hx_swap="innerHTML") if page < total_pages else
            Button("Next", disabled=True),
            cls="controls",
        ),
        cls="pagination",
    )


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

GLOBAL_NOTES_KEY = '_global'


@rt("/")
def dashboard():
    stats = db.get_dashboard_stats()
    notes = db.get_site_notes(GLOBAL_NOTES_KEY)
    return page_layout(
        Div(
            Div(H1("Wisconsin BRRTS Site Browser"), cls="page-header"),

            _wisdom_section(GLOBAL_NOTES_KEY, notes,
                            title="Qualification Wisdom",
                            placeholder="Add general notes about scraping strategy, qualification criteria..."),

            # KPI row
            Div(
                kpi_card(stats['total_sites'], "Total Sites", href="/sites"),
                kpi_card(stats['open_sites'], "Open", href="/sites?status=OPEN"),
                kpi_card(stats['closed_sites'], "Closed", href="/sites?status=CLOSED"),
                kpi_card(stats['total_actions'], "Total Actions"),
                kpi_card(stats['with_substances'], "With Substances", href="/sites?has_substances=1"),
                kpi_card(stats['with_documents'], "Sites with Docs", href="/sites?has_documents=1"),
                kpi_card(stats['pfas_sites'], "PFAS Flagged", href="/sites?pfas_flag=1"),
                cls="kpi-grid",
            ),

            # Breakdowns
            Div(
                Div(
                    # By type
                    Div(
                        Div(H2("By Activity Type"), cls="card-header"),
                        Div(
                            *[Div(
                                A(row['activity_type'], href=f"/sites?activity_type={row['activity_type']}"),
                                Span(f"{row['count']:,}"),
                                cls="breakdown-row",
                            ) for row in stats['by_type']],
                        ),
                        cls="card",
                    ),
                    # By status
                    Div(
                        Div(H2("By Status"), cls="card-header"),
                        Div(
                            *[Div(
                                A(row['status'], href=f"/sites?status={row['status']}"),
                                Span(f"{row['count']:,}"),
                                cls="breakdown-row",
                            ) for row in stats['by_status']],
                        ),
                        cls="card",
                    ),
                    style="display:grid; grid-template-columns: 1fr 1fr; gap: 20px;",
                ),
            ),

            # Top counties
            Div(
                Div(H2("Top Counties"), cls="card-header"),
                Div(
                    *[Div(
                        A(row['county'], href=f"/sites?county={row['county']}"),
                        Span(f"{row['count']:,}"),
                        cls="breakdown-row",
                    ) for row in stats['by_county']],
                ),
                cls="card",
                style="margin-top: 20px;",
            ),
        ),
        active='/',
    )


# ---------------------------------------------------------------------------
# Sites list
# ---------------------------------------------------------------------------

def _clean_filter(value: str, valid_values: set = None) -> str:
    if not value or value.startswith('All '):
        return ''
    if valid_values and value not in valid_values:
        return ''
    return value


def _get_filter_params(activity_type, status,
                       county, search, sort, order,
                       has_substances='', has_documents='', pfas_flag=''):
    activity_type = _clean_filter(activity_type)
    status = _clean_filter(status)
    county = _clean_filter(county)
    return {
        'activity_type': activity_type,
        'status': status,
        'county': county,
        'search': search or '',
        'sort': sort or 'start_date',
        'order': order or 'desc',
        'has_substances': has_substances or '',
        'has_documents': has_documents or '',
        'pfas_flag': pfas_flag or '',
    }


def sites_table_content(sites, total, page, per_page, sort, order, params):
    if not sites:
        return empty_state("No sites match your filters", "Try adjusting your search or filters")

    headers = Tr(
        sortable_header("BRRTS #", "brrts_number", sort, order, "/sites/table", params),
        sortable_header("Activity Name", "activity_name", sort, order, "/sites/table", params),
        sortable_header("Type", "activity_type", sort, order, "/sites/table", params),
        sortable_header("Status", "status", sort, order, "/sites/table", params),
        sortable_header("County", "county", sort, order, "/sites/table", params),
        sortable_header("Start", "start_date", sort, order, "/sites/table", params),
        sortable_header("End", "end_date", sort, order, "/sites/table", params),
        sortable_header("Actions", "action_count", sort, order, "/sites/table", params),
        sortable_header("Docs", "document_count", sort, order, "/sites/table", params),
    )

    rows = [Tr(
        Td(A(s['brrts_number'], href=f"/sites/{s['brrts_number']}")),
        Td(format_value(s['activity_name'])),
        Td(badge(s['activity_type'], type_variant(s['activity_type']))),
        Td(badge(s['status'], status_variant(s['status']))),
        Td(format_value(s['county'])),
        Td(format_date(s['start_date'])),
        Td(format_date(s['end_date'])),
        Td(str(s['action_count'] or 0)),
        Td(str(s.get('document_count') or 0)),
    ) for s in sites]

    return Div(
        Table(Thead(headers), Tbody(*rows), cls="data-table"),
        pagination_controls(page, total, per_page, "/sites/table", params),
    )


@rt("/sites")
def sites_list(request,
               activity_type: str = '', status: str = '',
               county: str = '',
               search: str = '', sort: str = 'start_date',
               order: str = 'desc', page: int = 1,
               has_substances: str = '', has_documents: str = '', pfas_flag: str = ''):
    per_page = 25
    options = db.get_filter_options()
    params = _get_filter_params(activity_type, status,
                                county, search, sort, order,
                                has_substances, has_documents, pfas_flag)
    sites, total = db.get_sites(
        activity_type=params['activity_type'], status=params['status'],
        county=params['county'],
        search=params['search'], sort=params['sort'], order=params['order'],
        has_substances=params['has_substances'], has_documents=params['has_documents'],
        pfas_flag=params['pfas_flag'],
        page=page, per_page=per_page,
    )

    filters = Div(
        Div(
            A("Clear filters", href="/sites", cls="clear-filters-btn"),
            cls="filter-bar",
        ),
        Div(
            Select(
                Option("All Types", value=""),
                *[Option(v, value=v, selected=(v == activity_type)) for v in options['activity_types']],
                name="activity_type",
                hx_get="/sites/table", hx_target="#table-content", hx_swap="innerHTML",
                hx_include="[name]", hx_trigger="change",
            ),
            Select(
                Option("All Statuses", value=""),
                *[Option(v, value=v, selected=(v == status)) for v in options['statuses']],
                name="status",
                hx_get="/sites/table", hx_target="#table-content", hx_swap="innerHTML",
                hx_include="[name]", hx_trigger="change",
            ),
            Select(
                Option("All Counties", value=""),
                *[Option(v, value=v, selected=(v == county)) for v in options['counties']],
                name="county",
                hx_get="/sites/table", hx_target="#table-content", hx_swap="innerHTML",
                hx_include="[name]", hx_trigger="change",
            ),
            Input(
                type="text", name="search", value=search,
                placeholder="Search name, BRRTS #, or address...",
                hx_get="/sites/table", hx_target="#table-content", hx_swap="innerHTML",
                hx_include="[name]", hx_trigger="keyup changed delay:300ms",
            ),
            Input(type="hidden", name="sort", value=sort),
            Input(type="hidden", name="order", value=order),
            Input(type="hidden", name="has_substances", value=has_substances),
            Input(type="hidden", name="has_documents", value=has_documents),
            Input(type="hidden", name="pfas_flag", value=pfas_flag),
            cls="filter-row",
        ),
    )

    table_content = sites_table_content(sites, total, page, per_page, sort, order, params)

    # Build active filter notice
    active_filters = []
    if has_substances == '1':
        active_filters.append("With Substances")
    if has_documents == '1':
        active_filters.append("With Documents")
    if pfas_flag == '1':
        active_filters.append("PFAS Flagged")

    filter_notice = None
    if active_filters:
        filter_notice = Div(
            Span("Filtered: ", style="font-weight: 600;"),
            ", ".join(active_filters),
            " — ",
            A("Clear all filters", href="/sites"),
            cls="notice notice-info",
        )

    return page_layout(
        Div(
            Div(
                H1("Sites"),
                Span(f"{total:,}", cls="count", id="site-count"),
                cls="page-header",
            ),
            filter_notice,
            Div(
                filters,
                Div(table_content, id="table-content"),
                cls="card",
            ),
        ),
        active='/sites',
    )


@rt("/sites/table")
def sites_table_partial(request,
                        activity_type: str = '', status: str = '',
                        county: str = '',
                        search: str = '', sort: str = 'start_date',
                        order: str = 'desc', page: int = 1,
                        has_substances: str = '', has_documents: str = '', pfas_flag: str = ''):
    per_page = 25
    params = _get_filter_params(activity_type, status,
                                county, search, sort, order,
                                has_substances, has_documents, pfas_flag)
    sites, total = db.get_sites(
        activity_type=params['activity_type'], status=params['status'],
        county=params['county'],
        search=params['search'], sort=params['sort'], order=params['order'],
        has_substances=params['has_substances'], has_documents=params['has_documents'],
        pfas_flag=params['pfas_flag'],
        page=page, per_page=per_page,
    )

    table_content = sites_table_content(sites, total, page, per_page, sort, order, params)

    is_htmx = request.headers.get('HX-Request') == 'true'
    if is_htmx:
        count_oob = Span(f"{total:,}", cls="count", id="site-count", hx_swap_oob="true")
        return (count_oob, table_content)

    return table_content


# ---------------------------------------------------------------------------
# Site detail
# ---------------------------------------------------------------------------

@rt("/sites/{brrts_number}")
def site_detail(brrts_number: str):
    site = db.get_site(brrts_number)
    if not site:
        return page_layout(
            Div(
                A("← Back to Sites", href="/sites", cls="back-btn"),
                empty_state("Site Not Found", f"No site with BRRTS number '{brrts_number}'."),
            ),
            active='/sites',
        )

    actions = db.get_site_actions(brrts_number)
    substances = db.get_site_substances(brrts_number)
    documents = db.get_site_documents(brrts_number)
    selections = db.get_site_selections(brrts_number)
    notes = db.get_site_notes(brrts_number)

    # Header
    header = Div(
        Div(
            H1(format_value(site['activity_name']), cls="detail-title"),
            Div(format_value(site['address']), cls="detail-subtitle"),
        ),
        Div(
            badge(site['brrts_number'], 'blue'),
            badge(site['activity_type'], type_variant(site['activity_type'])),
            badge(site['status'], status_variant(site['status'])),
            cls="detail-badges",
        ),
        cls="detail-header",
    )

    # Wisdom section
    wisdom_section = _wisdom_section(brrts_number, notes)

    # Flags section
    flag_names = [
        ('pecfa_flag', 'PECFA Eligible'),
        ('drycleaner_flag', 'Drycleaner'),
        ('co_contamination_flag', 'Co-Contamination'),
        ('npl_flag', 'NPL'),
        ('derf_flag', 'DERF'),
        ('pfas_flag', 'PFAS'),
        ('sediments_flag', 'Sediments'),
        ('petrol_ust_flag', 'Petroleum UST'),
    ]
    active_flags = [label for key, label in flag_names if site.get(key)]
    flags_section = None
    if active_flags:
        flags_section = Div(
            Div(H2("Flags"), cls="card-header"),
            Div(
                *[Span(f, cls="badge badge-red badge-lg", style="margin: 3px;") for f in active_flags],
                style="padding: 16px 20px; display: flex; flex-wrap: wrap;",
            ),
            cls="card",
        )

    # Site info card
    site_info = Div(
        Div(H2("Site Information"), cls="card-header"),
        Div(
            Div(Div("BRRTS Number", cls="label"), Div(format_value(site['brrts_number']), cls="value"), cls="detail-item"),
            Div(Div("Activity Type", cls="label"), Div(format_value(site['activity_type']), cls="value"), cls="detail-item"),
            Div(Div("Status", cls="label"), Div(format_value(site['status']), cls="value"), cls="detail-item"),
            Div(Div("County", cls="label"), Div(format_value(site['county']), cls="value"), cls="detail-item"),
            Div(Div("Address", cls="label"), Div(format_value(site['address']), cls="value"), cls="detail-item"),
            Div(Div("Municipality", cls="label"), Div(format_value(site['municipality']), cls="value"), cls="detail-item"),
            Div(Div("Zip Code", cls="label"), Div(format_value(site['zip_code']), cls="value"), cls="detail-item"),
            Div(Div("Region", cls="label"), Div(format_value(site['region']), cls="value"), cls="detail-item"),
            Div(Div("Location Name", cls="label"), Div(format_value(site['location_name']), cls="value"), cls="detail-item"),
            Div(Div("FID Number", cls="label"), Div(format_value(site['fid_number']), cls="value"), cls="detail-item"),
            Div(Div("Start Date", cls="label"), Div(format_date(site['start_date']), cls="value"), cls="detail-item"),
            Div(Div("End Date", cls="label"), Div(format_date(site['end_date']), cls="value"), cls="detail-item"),
            Div(Div("Last Action", cls="label"), Div(format_date(site['last_action']), cls="value"), cls="detail-item"),
            Div(Div("Responsible Party", cls="label"), Div(format_value(site['responsible_party']), cls="value"), cls="detail-item"),
            Div(Div("Project Manager", cls="label"), Div(format_value(site['project_manager']), cls="value"), cls="detail-item"),
            Div(Div("Latitude", cls="label"), Div(format_value(site['latitude']), cls="value"), cls="detail-item"),
            Div(Div("Longitude", cls="label"), Div(format_value(site['longitude']), cls="value"), cls="detail-item"),
            cls="detail-grid",
        ),
        cls="card",
    )

    # Activity comment
    comment_section = None
    if site.get('activity_comment'):
        comment_section = Div(
            Div(H2("Activity Comment"), cls="card-header"),
            Div(P(site['activity_comment'], style="white-space: pre-wrap; font-size: 14px; line-height: 1.6; color: #334155;"),
                style="padding: 16px 20px;"),
            cls="card",
        )

    # Documents section
    selected_count = len(selections)
    total_docs = len(documents)
    docs_section = None
    if documents:
        docs_header = _docs_header(selected_count, total_docs, brrts_number)
        doc_rows = [_doc_row(d, brrts_number, d['id'] in selections) for d in documents]
        docs_section = Div(
            docs_header,
            Table(
                Thead(Tr(
                    Th("", style="width:40px;"),
                    Th("Category"),
                    Th("Date"),
                    Th("Action Code"),
                    Th("Name"),
                    Th("Comment"),
                    Th("Link"),
                )),
                Tbody(*doc_rows),
                cls="data-table",
            ),
            cls="card",
        )

    # Substances section
    substances_section = None
    if substances:
        substance_tags = []
        for s in substances:
            amount_info = ""
            if s.get('released_amount') and s.get('released_unit'):
                amount_info = f" ({s['released_amount']} {s['released_unit']})"
            elif s.get('released_amount'):
                amount_info = f" ({s['released_amount']})"
            substance_tags.append(
                Span(f"{s['substance_name']}{amount_info}", cls="substance-tag")
            )
        substances_section = Div(
            Div(H2(f"Substances ({len(substances)})"), cls="card-header"),
            Div(*substance_tags, style="padding: 16px 20px; display: flex; flex-wrap: wrap;"),
            cls="card",
        )

    # Actions section
    actions_section = None
    if actions:
        action_items = []
        for a in actions:
            desc_parts = []
            if a.get('action_desc'):
                desc_parts.append(a['action_desc'])
            if a.get('action_comment'):
                desc_parts.append(a['action_comment'])
            desc_text = " — ".join(desc_parts) if desc_parts else None
            action_items.append(Div(
                Div(format_date(a['action_date']), cls="action-date") if a.get('action_date') else None,
                Div(format_value(a['action_name']), cls="action-name"),
                Div(desc_text, cls="action-desc") if desc_text else None,
                cls="action-item",
            ))
        actions_section = Div(
            Div(H2(f"Actions ({len(actions)})"), cls="card-header"),
            Div(*action_items, style="padding: 12px 20px; max-height: 600px; overflow-y: auto;"),
            cls="card",
        )

    # DNR link
    dnr_link = None
    if site.get('source_url'):
        dnr_link = A("View on WI DNR ↗", href=site['source_url'], target="_blank",
                     rel="noopener noreferrer", style="font-size:13px; color:#2563eb; margin-left:16px;")

    return page_layout(
        Div(
            Div(
                A("← Back to Sites", href="javascript:void(0)", onclick="history.back()", cls="back-btn"),
                dnr_link,
            ),
            header,
            wisdom_section,
            flags_section,
            docs_section,
            site_info,
            comment_section,
            substances_section,
            actions_section,
        ),
        active='/sites',
    )


# ---------------------------------------------------------------------------
# Document selection
# ---------------------------------------------------------------------------

def _docs_header(selected_count: int, total_docs: int, brrts_number: str):
    if total_docs > 0 and selected_count > 0:
        count_text = Span(f" ({selected_count} of {total_docs} selected for review)", cls="docs-header-count")
    elif total_docs > 0:
        count_text = Span(f" ({total_docs})", cls="docs-header-count")
    else:
        count_text = Span(" (0)", cls="docs-header-count")
    return Div(
        H2("Documents", count_text),
        cls="card-header",
        id=f"docs-header-{brrts_number}",
    )


def _doc_row(doc: dict, brrts_number: str, is_selected: bool):
    doc_id = doc['id']
    row_cls = "doc-selected" if is_selected else ""
    return Tr(
        Td(Input(
            type="checkbox",
            checked=is_selected,
            cls="uk-checkbox doc-checkbox",
            hx_post=f"/sites/{brrts_number}/docs/{doc_id}/toggle",
            hx_target="closest tr",
            hx_swap="outerHTML",
        )),
        Td(doc.get('document_category') or '--'),
        Td(format_date(doc.get('document_date'))),
        Td(doc.get('action_code') or '--'),
        Td(doc.get('action_name') or doc.get('title') or '--'),
        Td(doc.get('comment') or '--'),
        Td(A("View ↗", href=doc['document_url'], target="_blank",
              rel="noopener noreferrer") if doc.get('document_url') else '--'),
        cls=row_cls,
        id=f"doc-row-{doc_id}",
    )


@rt("/sites/{brrts_number}/docs/{doc_id:int}/toggle", methods=["POST"])
def toggle_doc_selection(brrts_number: str, doc_id: int):
    now_selected = db.toggle_document_selection(doc_id, brrts_number)

    doc = db.query_one(
        """SELECT id, title, document_date, document_type, document_url,
                  document_category, action_code, action_name, comment
           FROM documents WHERE id = ?""",
        (doc_id,)
    )
    if not doc:
        return P("Document not found.")

    updated_row = _doc_row(doc, brrts_number, now_selected)

    selected_count = db.get_selection_count(brrts_number)
    total_docs = db.scalar(
        "SELECT COUNT(*) FROM documents WHERE brrts_number = ?",
        (brrts_number,)
    ) or 0
    oob_header = _docs_header(selected_count, total_docs, brrts_number)
    oob_header.attrs['hx-swap-oob'] = 'true'

    return (updated_row, oob_header)


# ---------------------------------------------------------------------------
# Wisdom / qualification notes
# ---------------------------------------------------------------------------

def _wisdom_section(brrts_number: str, notes: list[dict],
                    title: str = "Qualification Wisdom",
                    placeholder: str = "Add qualification notes about this site..."):
    note_count = len(notes)
    count_text = Span(f" ({note_count})", cls="docs-header-count") if note_count else ""

    content_id = f"wisdom-content-{brrts_number}"
    input_id = f"wisdom-input-{brrts_number}"
    return Div(
        Div(H2(title, count_text), cls="card-header", id=f"wisdom-header-{brrts_number}"),
        Div(
            Div(
                Textarea(
                    name="note_text",
                    placeholder=placeholder,
                    cls="wisdom-textarea",
                    id=input_id,
                    hx_post=f"/sites/{brrts_number}/notes",
                    hx_target=f"#{content_id}",
                    hx_swap="innerHTML",
                    hx_trigger="keyup changed delay:1000ms",
                    hx_include="this",
                ),
                Div(
                    Button("Save", cls="wisdom-save-btn",
                           hx_post=f"/sites/{brrts_number}/notes",
                           hx_target=f"#{content_id}",
                           hx_swap="innerHTML",
                           hx_include=f"#{input_id}"),
                    Span("", id=f"wisdom-status-{brrts_number}", cls="wisdom-save-status"),
                    cls="wisdom-actions",
                ),
                style="padding: 16px 20px 8px;",
            ),
            _wisdom_timeline(notes),
            id=content_id,
        ),
        cls="card",
    )


def _wisdom_content(brrts_number: str, notes: list[dict], just_saved: bool = False,
                    placeholder: str = "Add qualification notes about this site..."):
    content_id = f"wisdom-content-{brrts_number}"
    input_id = f"wisdom-input-{brrts_number}"
    return Div(
        Div(
            Textarea(
                name="note_text",
                placeholder=placeholder,
                cls="wisdom-textarea",
                id=input_id,
                hx_post=f"/sites/{brrts_number}/notes",
                hx_target=f"#{content_id}",
                hx_swap="innerHTML",
                hx_trigger="keyup changed delay:1000ms",
                hx_include="this",
            ),
            Div(
                Button("Save", cls="wisdom-save-btn",
                       hx_post=f"/sites/{brrts_number}/notes",
                       hx_target=f"#{content_id}",
                       hx_swap="innerHTML",
                       hx_include=f"#{input_id}"),
                Span("Saved", id=f"wisdom-status-{brrts_number}", cls="wisdom-save-status") if just_saved else
                Span("", id=f"wisdom-status-{brrts_number}", cls="wisdom-save-status"),
                cls="wisdom-actions",
            ),
            style="padding: 16px 20px 8px;",
        ),
        _wisdom_timeline(notes),
        id=content_id,
    )


def _wisdom_timeline(notes: list[dict]):
    if not notes:
        return Div(id="wisdom-timeline")
    return Div(
        *[_wisdom_note(n) for n in notes],
        cls="wisdom-timeline",
        id="wisdom-timeline",
    )


def _wisdom_note(note: dict):
    return Div(
        Div(format_date(note['created_at']), cls="wisdom-timestamp"),
        Div(note['note_text'], cls="wisdom-text"),
        cls="wisdom-note",
    )


@rt("/sites/{brrts_number}/notes", methods=["POST"])
async def save_note(brrts_number: str, request):
    form = await request.form()
    note_text = (form.get('note_text') or '').strip()

    if note_text:
        db.add_site_note(brrts_number, note_text)

    notes = db.get_site_notes(brrts_number)

    is_global = (brrts_number == GLOBAL_NOTES_KEY)
    title = "Qualification Wisdom"
    placeholder = ("Add general notes about scraping strategy, qualification criteria..."
                   if is_global else "Add qualification notes about this site...")

    note_count = len(notes)
    count_text = Span(f" ({note_count})", cls="docs-header-count") if note_count else ""
    oob_header = Div(H2(title, count_text), cls="card-header",
                     id=f"wisdom-header-{brrts_number}")
    oob_header.attrs['hx-swap-oob'] = 'true'

    content = _wisdom_content(brrts_number, notes, just_saved=bool(note_text),
                              placeholder=placeholder)
    return (content, oob_header)


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import os
    import uvicorn
    port = int(os.environ.get('PORT', 5010))
    uvicorn.run(app, host="0.0.0.0", port=port)
