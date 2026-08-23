# Middesk Connector — Connector Discovery

**Дата discovery:** 2026-08-22 (сессия продолжена 2026-08-23 по часам пользователя)
**Статус:** Ярусы 1-3 пройдены (чтение официальной документации
docs.middesk.com, 2026-08-22/23, включая llms.txt-индекс, webhooks,
security, environments). Задача #2302 явно заявляла "максимальная форма со
всеми доступными функциями с их стороны и всеми возможными функциями
внутри нашего приложения" — трактуется как заранее заявленное решение
объёма ("максимум"), тот же прецедент, что CircleCI/GitLab CI/CD/MuleSoft/
Power Automate/UiPath/Blue Prism/Automation Anywhere/Cin7 Core/ShipStation/
PagerDuty/DocuSign/Ironclad коннекторы: §7 (решение по объёму) не требует
повторного вопроса Владу.

---

## 1. Целевой сервис и источники

Middesk — специализированный B2B KYB (Know Your Business) / business
identity verification & risk API, используемый в fintech/banking/
insurance/marketplace underwriting для проверки контрагентов-юрлиц.
Прочитаны 2026-08-22/23:

- `docs.middesk.com/llms.txt` — полный индекс документации и REST API
  Docs-раздела (подтверждено полным обходом: Business Verification,
  Entity Management, Agents, Prefill, Webhooks, Documents, Risk
  Assessments)
- `docs.middesk.com/how-middesk-works` — модель Business lifecycle,
  Orders, Tasks, environments
- `docs.middesk.com/lifecycle-of-business` — стадии статуса Business:
  `open → pending → in_audit → in_review → approved/rejected`
- `docs.middesk.com/build/api-keys` — Basic Auth (API key как username)
  или Bearer Auth (`Authorization: Bearer mk_live_...`), два раздельных
  ключа (`mk_test_...` / `mk_live_...`) под два раздельных base URL
- `docs.middesk.com/environments` — sandbox (`api-sandbox.middesk.com`)
  vs production (`api.middesk.com`), ключ и URL обязаны совпадать, иначе
  запрос отклоняется; подробная таблица sandbox trigger values для
  тестовых сценариев (не переносится в код коннектора — справочно)
- `docs.middesk.com/build/webhooks` — событийная модель, `include`-
  фильтрация ассоциаций, кастомные webhook event schemas на GraphQL-
  selection-set, полный список типов событий (Core/Agent/Monitor)
- `docs.middesk.com/build/secure-webhooks` — HMAC-SHA256 подпись
  (`X-Middesk-Signature-256`), альтернативы: Mutual TLS, OAuth access
  tokens через OIDC
- `docs.middesk.com/openapi.json` / `openapi.yaml` — официальная OpenAPI
  3.1 спецификация (структурный источник полного списка операций)
- Раздел "API Docs" в llms.txt — явный список всех REST-эндпоинтов по
  категориям: Business Verification (Businesses, Orders, Business
  Batches, Signals, Monitoring, Liens, Registrations, Lien Terminations,
  Policy Results, Reviews, Actions, Tin Match, Websites, Connections,
  Timeline), Entity Management (Registration Requests, Information
  Requests, Applications, Companies, Jurisdictions, Questions, Mail),
  Agents (Agents, Threads, Runs — включая SSE streaming), Prefill
  (Autocomplete Identities, Smart Populate), Webhooks (webhooks +
  webhook event schemas + OIDC keys), Documents, Risk Assessments

## 2. КРИТИЧНО: Middesk — это ЧЕТЫРЕ функциональных продукта под одним
API-ключом, не один монолитный "verify" вызов

Middesk продаёт несколько разных по назначению продуктов, все доступные
через один и тот же API-ключ и base URL, но с существенно разной моделью
данных:

- **Business Verification (KYB)** — основной и самый зрелый модуль:
  `Business` объект как корневая сущность, к которой привязываются
  `Order`ы на конкретные продукты верификации (`identity`, `tin`,
  `watchlist`, `industry_classification`, `web_presence`, `risk`,
  `signal` и др.), результаты сводятся в `Review` с иерархией `Review
  Task`ов по категориям (name, address, tin, sos, watchlist, kyc,
  adverse_media, liens, bankruptcies, litigations, people и т.д.).
  Плюс отдельные подпродукты: Liens (UCC/tax lien search + filing +
  termination), Registrations (создание SOS-регистрации напрямую),
  Business Batches (bulk-загрузка множества businesses разом), Signals
  (быстрый score-based результат для онбординга), Monitoring (подписка
  на будущие изменения по уже верифицированному Business), Policy
  Results (автоматизированные approve/reject решения по заранее
  настроенным правилам), Actions (пост-фактум операции над завершённым
  Business — добавить источник данных, изменить TIN, сменить decision),
  Connections (обнаружение связанных businesses через общих людей/
  адреса), Timeline (хронология изменений SOS-регистрации), TIN Match
  (доступность сервиса сверки TIN), Websites (веб-анализ бизнеса).
  **Это основной охват коннектора.**
- **Entity Management** — ОТДЕЛЬНЫЙ продукт с полностью другим жизненным
  циклом: регистрация работодателей на payroll-налоги в разных штатах.
  Своя модель (`Registration Request` → `Application` → `Company`,
  `Jurisdiction` поиск, `Question`/`Mail` как побочные сущности рабочего
  процесса). Сознательно НЕ КYB, это administrative tax-registration
  workflow — включается в охват как отдельная группа handlers, не
  смешивается с Business Verification моделью.
- **Agents** — новый AI-agent слой поверх верификации (`Agent`, `Thread`,
  `Run` + Server-Sent Events streaming + "interrupt policy" для
  человеческого review находок агента перед действием). Экспериментальный
  по духу (agentic workflow поверх остальных продуктов), но с
  документированным публичным API — включается как отдельная группа с
  явной пометкой "агентный слой, результаты которого могут требовать
  ручного review через interrupt policy".
- **Prefill/Risk** — вспомогательные быстрые операции для онбординга:
  Autocomplete Identities (автодополнение имени/адреса бизнеса по
  частичному вводу), Smart Populate (синхронный prefill данных
  бизнеса), Risk Assessments (получение отдельного scored risk-снапшота,
  включая identifier-level и dimension-level детализацию).

**Решение:** охватываем ВСЕ четыре продукта максимально широко (по прямому
указанию пользователя "максимальная форма"), но явно разносим по разным
файлам handlers (`handlers_business.py`, `handlers_orders.py`,
`handlers_monitoring.py`, `handlers_liens.py`, `handlers_entity_mgmt.py`,
`handlers_agents.py`, `handlers_prefill_risk.py`, `handlers_webhooks.py`,
`handlers_documents.py`) — не в одну кучу, тот же принцип разделения, что
Salesforce Connector (Metadata/Bulk/Composite отдельными файлами) и
DocuSign Connector (envelope/template/bulk_send/account отдельными
файлами).

## 3. Модель асинхронной верификации — центральное архитектурное решение

Middesk не даёт синхронного "verify этот бизнес и получи результат сразу"
(за исключением Smart Populate/Autocomplete/Signal — которые
специально спроектированы как быстрые синхронные операции). Основной
KYB-поток асинхронный:

1. `POST /v1/businesses` — создать Business с минимальными данными (имя,
   опционально адрес/TIN/website)
2. `POST /v1/businesses/{id}/orders` — создать один или несколько Order
   на конкретный продукт (`identity` — базовая верификация имени/адреса/
   SOS/TIN/people, `tin`, `watchlist`, `industry_classification`,
   `web_presence`, `risk`)
3. Middesk асинхронно (обычно секунды-минуты, иногда с задержкой
   Analyst-in-the-Loop до нескольких минут) заполняет Business данными:
   `registrations`, `people` (owners/officers), `tin`, `addresses`,
   `formation`, `watchlist`, `industry_classification`, `website`,
   `documents`, `liens`, `bankruptcies`, `litigations`
4. Формируется `Review` с массивом `Review Task`ов — каждый со своей
   `category`/`key`/итоговым `outcome` (pass/fail/review needed)
5. `status` бизнеса проходит `open → pending → in_audit → in_review →
   approved/rejected`
6. Изменения приходят через вебхуки (`business.created`,
   `business.updated`, `order.created`, `order.updated`) — рекомендуемый
   Middesk способ вместо polling

**Решение:** коннектор явно моделирует это как раздельные
`create_business` + `create_order` + `get_business` (плюс отдельно
`get_business_review`), НЕ как единую "verify_business" функцию, которая
бы скрывала асинхронность и создавала ложное ожидание мгновенного
результата. Ради удобства добавляется один value-add wrapper
`create_and_verify_business` (Tier 3), который создаёт Business + сразу
Order(ы) на identity/tin/watchlist одним вызовом — но статус всё равно
остаётся асинхронным, отчёт явно об этом предупреждает.

## 4. Окружения — sandbox / production, ключ и URL обязаны совпадать

Аналогично Stripe/Shopify/DocuSign sandbox_mode, но здесь физически
разные API-домены, а не query-флаг:

- Sandbox: `https://api-sandbox.middesk.com/v1/`, ключ с префиксом
  `mk_test_...`
- Production: `https://api.middesk.com/v1/`, ключ с префиксом
  `mk_live_...`

Middesk явно документирует: "The API key type and URL must match. You
cannot use a production key with a sandbox URL or the other way around."
— коннектор просит пользователя выбрать среду при подключении (по
умолчанию sandbox для безопасного первого теста, тот же паттерн, что
`sandbox_mode` у Stripe/Shopify Connector), хранит выбор в connection
record, использует его для выбора правильного base URL на каждом вызове.

## 5. Авторизация — BYOK API key, Basic или Bearer Auth

Middesk не предлагает OAuth для обычных API-клиентов (OIDC упоминается
только как альтернативная опция для верификации ВХОДЯЩИХ webhook-запросов,
не для исходящих вызовов коннектора). Модель — классический BYOK API key,
тот же паттерн, что Cin7 Core/CircleCI/ShipStation/PagerDuty/UiPath: два
поля при подключении — `api_key` и `environment` (`sandbox`/`production`).
Auth-заголовок: `Authorization: Bearer {api_key}` (Bearer Auth выбран
вместо Basic — чище для передачи через существующий secrets-паттерн,
никакой разницы для Middesk по документации).

## 6. Вебхуки — Egress-подписка, Imperal как получатель

Middesk поддерживает регистрацию webhook endpoint URL (`POST /v1/webhooks`)
с подпиской на список типов событий и HMAC-SHA256 подписью запроса
(`X-Middesk-Signature-256` заголовок, секрет выдаётся при создании
webhook). Реализуется управление подписками (create/list/get/update/
delete webhook) как обычные CRUD-функции коннектора — тот же паттерн,
что Stripe/GitLab/CircleCI `create_webhook`/`list_webhooks`/
`delete_webhook`. Приём и обработка входящих событий (сервер, который бы
слушал `X-Middesk-Signature-256`) — вне периметра коннектора текущей
архитектуры (как и у большинства коннекторов портфеля): коннектор
регистрирует/управляет подписками, а не поднимает webhook receiver.

## 7. Решение по объёму релиза (см. CONNECTOR_DISCOVERY_STANDARD.md §Шаг 4)

Пользователь явно сформулировал objем в задаче #2302: \"максимальная форма
со всеми доступными функциями с их стороны и всеми возможными функциями
внутри нашего приложения для повышения эффективности\" — трактуется как
заранее принятое решение в пользу МАКСИМУМА (Ярус 1 + Ярус 2 + Ярус 3), без
повторного уточняющего вопроса, по прямому прецеденту CircleCI/GitLab
CI/CD/MuleSoft/Power Automate/UiPath/Blue Prism/Automation Anywhere/
Cin7 Core/ShipStation/PagerDuty/DocuSign/Ironclad. Ярусы:

- **Ярус 1 (must-have core KYB)**: connect/disconnect/list connections,
  create/get/list/update businesses, create/get/list orders, get business
  review + review tasks, list registrations, list people (owners/
  officers), get TIN details, get watchlist hits.
- **Ярус 2 (полнота охвата)**: liens (list/search/get + lien
  terminations), business batches (bulk create), signals, monitoring
  (create/list/get/delete monitor + monitor events), policy results,
  actions (post-decision operations), connections (related businesses),
  timeline, websites, TIN match availability, webhooks CRUD, documents
  list/get/download.
- **Ярус 3 (ценностные надстройки Imperal, Tier 3 value-add, наш
  собственный функционал сверху API)**: `create_and_verify_business`
  (создать Business + сразу Order(ы) на identity/tin/watchlist одним
  вызовом), `audit_verification_queue` (агрегированный отчёт: сколько
  businesses в каждом статусе, сколько review tasks требуют внимания,
  средний SLA до approved), `get_high_risk_businesses_report`
  (value-add: отфильтровать businesses с failed review tasks в
  категориях watchlist/adverse_media/bankruptcies/liens), Entity
  Management (registration requests/applications/companies/
  jurisdictions/questions/mail — полный отдельный домен), Agents
  (agents/threads/runs — с явной пометкой interrupt-policy review),
  Prefill/Risk (autocomplete identities, smart populate, risk
  assessments).
