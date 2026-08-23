# Middesk Connector — Preparation

**Статус:** Фаза 1 (Discovery + архитектурные решения) завершена. Объём
релиза заявлен пользователем явно в задаче #2302 — "разработай это
приложение в максимальной форме со всеми доступными функциями с их
стороны и всеми возможными функциями внутри нашего приложения для
повышения эффективности" — трактуется как "максимум" (Ярус 1+2+3), по
прецеденту CircleCI/GitLab CI/CD/MuleSoft/Power Automate/UiPath/Blue
Prism/Automation Anywhere/Cin7 Core/ShipStation/PagerDuty/DocuSign/
Ironclad, где такая же явная формулировка уже освобождала от повторного
вопроса.

**Владелец продукта:** vlad@bluebeeweb.com
**Дата подготовки:** 2026-08-23, v0.1
**Vikunja task:** #2302 (BBW Imperal Apps), [App Development].

**Почему сейчас:** Middesk закрывает совершенно новую для портфеля Imperal
категорию — B2B KYB / business identity verification & risk intelligence.
В отличие от CRM (HubSpot/Salesforce), iPaaS (MuleSoft/Make/n8n/Workato),
RPA (UiPath/Automation Anywhere/Blue Prism), e-signature (DocuSign) или
CLM (Ironclad), у Imperal нет ни одного коннектора для compliance/
underwriting/fraud-prevention домена. Middesk даёт клиентам Imperal в
fintech, lending, marketplace onboarding и payments risk возможность
проверять контрагентов-юрлиц прямо из Imperal: SOS-регистрация, TIN/EIN,
владельцы/officers, санкционные списки, adverse media, UCC/tax liens,
банкротства, судебные иски.

---

## 1. Паспорт приложения

**Название в Marketplace (display_name): «Middesk»**. Внутренний
app_id/папка: `middesk-connector`.

**Middesk Connector** — коннектор к Middesk API (`docs.middesk.com`),
покрывающий все четыре продуктовых домена: Business Verification (KYB) —
основной охват, Entity Management (payroll tax registration), Agents
(AI-agent слой поверх верификации), Prefill/Risk (быстрые onboarding-
проверки). BYOK: пользователь подключает свой собственный Middesk API
key (sandbox или production).

## 2. Архитектурные решения (ADR-style)

### ADR-1: BYOK API key (Bearer Auth), НЕ built-in ext.oauth

Middesk не входит в список платформенных OAuth-провайдеров (google/
microsoft/yahoo). У Middesk нет OAuth для клиентов API вообще — только
статический API key с двумя средами (`mk_test_...` / `mk_live_...`).
Тот же паттерн, что Cin7 Core/CircleCI/ShipStation/PagerDuty/UiPath:
`connect_middesk(api_key, environment)` сохраняет пару в secrets,
`_resolve_connection(ctx, connection_id)` подтягивает её на каждый вызов.

### ADR-2: environment (sandbox/production) как обязательное поле подключения,
не query-флаг

В отличие от Stripe/Shopify (`sandbox_mode` boolean на одном домене),
Middesk физически разводит sandbox/production на разные base URL
(`api-sandbox.middesk.com` vs `api.middesk.com`), и ключ должен совпадать
со средой. Коннектор хранит `environment` в connection record и выбирает
base URL детерминированно при каждом вызове; если пользователь передаёт
ключ не того типа (не начинается с ожидаемого префикса), `connect_middesk`
даёт понятную ошибку до сохранения, не полагаясь только на 401 от API.

### ADR-3: Асинхронная модель Business/Order/Review — НЕ единая
"verify_business" функция

Middesk не даёт мгновенного результата верификации (кроме нарочито
синхронных Prefill/Signal функций). Основной поток: `create_business` →
`create_order` (на конкретный продукт: identity/tin/watchlist/
industry_classification/web_presence/risk) → Middesk асинхронно
заполняет Business → `get_business`/`get_business_review` читают
накопленный результат. Коннектор моделирует это явно раздельными
функциями, чтобы не создавать ложного ожидания синхронности. Ради
удобства один Tier-3 wrapper `create_and_verify_business` объединяет
create_business + create_order(ы) в один вызов, но по-прежнему возвращает
асинхронный `pending`-статус, не притворяется, что результат уже готов.

### ADR-4: Отдельные файлы handlers по продуктовому домену

Тот же принцип, что Salesforce Connector (Metadata/Bulk/Composite) и
DocuSign Connector (envelope/template/bulk_send/account раздельно):
`handlers_connection.py`, `handlers_business.py`, `handlers_orders.py`,
`handlers_review.py`, `handlers_liens.py`, `handlers_monitoring.py`,
`handlers_batches_signals.py`, `handlers_webhooks.py`,
`handlers_entity_mgmt.py`, `handlers_agents.py`,
`handlers_prefill_risk.py`, `handlers_audit.py` (Tier 3 value-add
reports). Не сваливаем всё в один файл — так же, как AppFolio/Cin7 Core/
PagerDuty разносят по доменам.

### ADR-5: ctx-based secrets pattern (`_load_connections`/
`_save_connections`/`_resolve_connection`)

Тот же паттерн, что уже устоялся в Cin7 Core/PagerDuty/CircleCI/
GitLab CI/CD/ShipStation/DocuSign/Ironclad Connector — async
ctx.secrets-based storage хранит список подключений (может быть
несколько Middesk-аккаунтов у одного пользователя Imperal, например
sandbox + production параллельно), `connection_id` явно передаётся в
каждый вызов после `connect_middesk`.

### ADR-6: Webhooks — управление подписками, не receiver

Коннектор предоставляет CRUD над Middesk webhook subscriptions (какие
события Middesk должен слать и куда), но не поднимает сервер-приёмник
внутри Imperal для входящих событий — тот же паттерн, что у остальных
коннекторов портфеля (Stripe/GitLab/CircleCI: коннектор регистрирует
подписки, инфраструктура приёма отдельно).

## 3. ActionResult API contract (проверено на предыдущих связках)

Как подтверждено на AppFolio/Cin7 Core/PagerDuty/CircleCI/DocuSign/
Ironclad связках: `ActionResult.success(data, summary, *, ui=None,
refresh_panels=None)` и `ActionResult.error(error, retryable=False, *,
code='')` — единственные два реальных метода. `.ok(...)` НЕ существует в
imperal_sdk ни в одной проверенной версии — не использовать нигде в
handlers Middesk.
