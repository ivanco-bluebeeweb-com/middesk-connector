"""Panel UI -- connections list/connect form + help modal.

SIDEBAR CONTENT -- NO CARDS ANYWHERE, per ~/UI_INTERFACE_STANDARD.md's
"left sidebar, no decorated cards" rule (same convention as DocuSign
Connector's / CircleCI Connector's panels.py).

Every section (connections, connect form) is a plain ui.Stack, content
stacked vertically and left-aligned, sections separated by ui.Divider() --
no Card border/background/shadow anywhere in this slot. Disconnect lives
only in the "App settings" screen (panels_settings.py). The one secondary
"App settings" button is always the LAST element at the bottom of the
sidebar.

PER ~/UI_INTERFACE_STANDARD.md (2026-08-21 addendum): every Input carries
its own visible label (never placeholder-only), the placeholder text is
always contextually specific to what's being entered (never a generic
"Enter value"), the form's own container is stretched to the full width
of the left sidebar, and the form's inner content is stretched to fill
that container. The "How do I set this up?" instruction lives ONLY in
the help modal (middesk_connect_help below) -- it is not duplicated as
static sidebar text.
"""
from __future__ import annotations

from imperal_sdk import ui

from app import ext
import handlers_connection as h


def _settings_button() -> ui.UINode:
    """The one required secondary entry point into the settings screen --
    always the last element at the bottom of the sidebar."""
    return ui.Button(
        "App settings", variant="secondary", size="sm", full_width=True,
        icon="settings", on_click=ui.Call("__panel__middesk_settings"),
    )


def _connection_row(c: dict) -> ui.UINode:
    label = c.get("label") or "Middesk account"
    env = c.get("environment", "sandbox")
    detail = f"{'Production' if env == 'production' else 'Sandbox'} · {c.get('masked_api_key') or h._mask(c.get('api_key', ''))}"
    return ui.Stack(direction="v", gap=1, children=[
        ui.Text(label, variant="body"),
        ui.Text(detail, variant="caption"),
    ])


def _connections_section(connections: list[dict]) -> ui.UINode:
    if not connections:
        return ui.Text("No Middesk accounts connected yet.", variant="caption")
    children: list[ui.UINode] = []
    for i, c in enumerate(connections):
        if i > 0:
            children.append(ui.Divider())
        children.append(_connection_row(c))
    return ui.Stack(direction="v", gap=2, children=children)


def _connect_section() -> ui.UINode:
    """Form container stretched to the FULL WIDTH of the left sidebar, its
    inner content stretched to fill it (align="stretch" on both the outer
    Stack and the Form's own children Stack). No intro heading/description
    text here -- the setup walkthrough lives ONLY in middesk_connect_help's
    modal (button below opens it); repeating it here would duplicate that
    instruction."""
    return ui.Stack(direction="v", gap=3, align="stretch", children=[
        ui.Button("How do I set this up?", variant="ghost", size="sm",
                  icon="HelpCircle",
                  on_click=ui.Call("__panel__middesk_connect_help")),
        ui.Form(
            action="connect_middesk",
            submit_label="Verify and connect",
            children=[
                ui.Stack(direction="v", gap=1, align="stretch", children=[
                    ui.Text("Environment", variant="caption"),
                    ui.Select(param_name="environment",
                              options=[
                                  {"label": "Sandbox (test data)", "value": "sandbox"},
                                  {"label": "Production (live)", "value": "production"},
                              ],
                              value="sandbox"),
                ]),
                ui.Stack(direction="v", gap=1, align="stretch", children=[
                    ui.Text("API Key", variant="caption"),
                    ui.Password(param_name="api_key",
                                placeholder="mk_test_... (sandbox) or mk_live_... (production)"),
                ]),
                ui.Stack(direction="v", gap=1, align="stretch", children=[
                    ui.Text("Label (optional)", variant="caption"),
                    ui.Input(param_name="label",
                             placeholder="e.g. Underwriting prod or QA sandbox"),
                ]),
            ],
        ),
    ])


@ext.panel("middesk_connect", slot="left", title="Middesk", icon="🛡️",
           default_width=340, min_width=280, max_width=440)
async def middesk_connect_panel(ctx, **kwargs) -> object:
    connections = await h._load_connections(ctx)
    connected = bool(connections)

    header = ui.Header(text="Middesk", level=2,
                        subtitle="Verify businesses (KYB) and monitor risk from Imperal")

    if not connected:
        return ui.Stack(direction="v", gap=4, align="stretch", children=[
            header,
            _connect_section(),
            ui.Divider(),
            _settings_button(),
        ])

    return ui.Stack(direction="v", gap=4, align="stretch", children=[
        header,
        ui.Text("Connected accounts", variant="subtitle"),
        _connections_section(connections),
        ui.Divider(),
        _connect_section(),
        ui.Divider(),
        _settings_button(),
    ])


@ext.panel("middesk_connect_help", slot="center",
           title="How to connect Middesk", center_overlay=True)
async def middesk_connect_help(ctx, **kwargs) -> object:
    content = ui.Stack(direction="v", gap=3, children=[
        ui.Text("1. Log into your Middesk Dashboard at app.middesk.com."),
        ui.Text("2. Go to Settings > Developer > Credentials."),
        ui.Text("3. Copy your Test API key (starts with mk_test_) to try Middesk with mock data first, or your Live API key (starts with mk_live_) for real production checks."),
        ui.Text("4. Pick the matching environment here -- a sandbox key only works against sandbox, a live key only works against production."),
        ui.Text("5. Paste the key and connect. The connector checks it works before saving it."),
        ui.Divider(),
        ui.Alert(
            title="Business Verification API v1 scope",
            message=(
                "This manages Businesses, Orders, Reviews/Review Tasks, "
                "Monitors, Liens, Registrations, TIN, Documents, Websites, "
                "Business Batches, Signals, Policy Results, Actions, "
                "Webhooks, plus Entity Management (payroll tax "
                "registration) and Agents (AI verification threads/runs)."
            ),
            type="warning",
        ),
        ui.Divider(),
        ui.Link(
            label="Open Middesk's official API key guide",
            href="https://docs.middesk.com/build/api-keys",
        ),
    ])
    return ui.Dialog(
        title="How to connect Middesk",
        content=content,
        confirm_label="",
        cancel_label="Close",
    )


@ext.panel("middesk_center", slot="center", title="Middesk", icon="🛡️", center_overlay=True)
async def middesk_center_panel(ctx, **kwargs) -> object:
    """Base center panel -- per UI_INTERFACE_STANDARD.md (2026-08-20).
    This app has no list/detail content of its own to show in the center
    by default (everything lives in the sidebar). MUST carry
    center_overlay=True: per docs.imperal.io/en/concepts/panels, a plain
    slot="center" panel is registered but the Panel app never fetches it
    at session-init without that flag. Text is the shared canonical
    wording -- must stay identical across every app in this situation."""
    return ui.Empty(
        message="Nothing to show here -- this app is managed entirely from the sidebar.",
        icon="👈",
    )
