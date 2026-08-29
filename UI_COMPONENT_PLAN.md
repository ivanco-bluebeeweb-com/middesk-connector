# Middesk Connector — UI component plan

Источники: `Docs/session-notes/UI_COMPONENT_VOCABULARY.md`, `UI_INTERFACE_STANDARD.md`,
`concepts/panels.md`. Основано на функционале `middesk-connector`.

## 1. Компоненты

| Экран | Примитивы | Почему именно эти |
|---|---|---|
| Sidebar (left) | `ui.Column`(align="start") + `ui.Text`(account) + `ui.Divider` + navigation `ui.ListItem`(Business Verifications/Watchlists/Reports) + `ui.Button`("App settings") | Без карточек по стандарту. |
| Business Verification List (center, `center_overlay=True`) | `ui.Stats`(Verified/Pending/Flagged today) + `ui.Select`(status_filter) + `ui.DataTable`(business name, EIN, status Badge verified/pending/review_required, created; sortable) | `DataTable` — стандартный способ работать с потоком KYB-проверок бизнеса. |
| Business Detail | Back-button + `ui.KeyValue`(legal name/EIN/address/formation date/industry) + `ui.List`(officers/registered agents как ListItem) + `ui.Timeline`(verification stages: submitted→sos lookup→irs match→watchlist screen→decisioned) | `Timeline` отражает последовательность источников данных, опрашиваемых при верификации бизнеса. |
| Watchlist Screening Results | `ui.DataTable`(list name OFAC/PEP/etc, match found Badge yes/no, matched entity; sortable) | Табличный вывод результатов скрининга по каждому watchlist-источнику. |
| Review Required Queue | `ui.DataTable`(business, flagged reason, submitted date; sortable) + `ui.Row`(Button "Approve", "Reject", "Escalate") | Табличная очередь ручной проверки с прямыми действиями по строке. |
| Review Decision Dialog | `ui.Dialog`(title="Подтвердить решение по бизнесу?", content=`ui.TextArea`(param_name="review_note", placeholder="Причина решения..."), confirm_label="Подтвердить") | Комплаенс-решение — значимое, требует явного подтверждения с обоснованием. |
| Secretary of State (SOS) Filing Viewer | `ui.KeyValue`(filing status/registered agent/good standing) | Свед
... [22 chars elided from this argument for history replay -- the tool received the FULL value] ...
формация из filing штата — компактный набор полей. |
| Website/Presence Report | `ui.KeyValue`(domain age/social presence/reviews found) | Сводка проверки цифрового следа бизнеса. |
| App Settings | `ui.Accordion`([Connections+Disconnect, Environment sandbox/prod, Webhook URL]) | Централизованные настройки по стандарту. |

## 2. User flow (валидно по panel lifecycle)

1. **SESSION INIT** → `__panel__middesk_sidebar` рендерит account + разделы,
   `auto_action` открывает Business Verification List.
2. List: DataTable с status Badge → клик на строку → `ui.Call(business_id=...)`
   → Business Detail на том же center handler.
3. Business Detail: KeyValue + List(officers) + Timeline(stages источников
   данных) + ссылки на Watchlist Screening / SOS Filing (табы или отдельные
   Call на том же handler с параметром `view`).
4. Если статус "review_required" → доступ к Review Required Queue → Approve/
   Reject/Escalate → `Dialog` с обязательным `review_note` → `ui.Call` →
   `submit_review_decision` → `refresh_panels`.
5. "App settings" (нижняя кнопка сайдбара) → отдельный center handler
   `panels_settings.py`; "Disconnect" — единственное деструктивное действие,
   обёрнуто в `Dialog`.

## 3. Экраны/карточки (конкретно)

- **Screen: Business Verification List** — Stats(3) + Select(status) + DataTable(name/EIN/status/created).
- **Screen: Business Detail** — KeyValue(business fields) + List(officers) + Timeline(stages).
- **Screen: Watchlist Screening** — DataTable(list/match/entity).
- **Screen: Review Required Queue** — DataTable(business/reason/date) + Row(Approve/Reject/Escalate).
- **Screen: SOS Filing Viewer** — KeyValue(filing status/agent/good standing).
- **Screen: Website/Presence Report** — KeyValue(domain age/social/reviews).
- **Screen: App Settings** — Accordion(Connections, Environment, Webhook URL).
