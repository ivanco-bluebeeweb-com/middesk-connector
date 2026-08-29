# Middesk Connector — идеальный первый запуск

Источник: `ONBOARDING_FIRST_LAUNCH_STANDARD.md`. Целевой пользователь: Risk/Compliance-
специалист fintech/B2B-платформы на Middesk (KYB).

## 1. Credential type
API key с явным префиксом окружения (`mk_test_...`/`mk_live_...`) + environment select.

## 2. Идеальный флоу
1. **Первое открытие** — `Empty` со ссылкой на Middesk Dashboard > API keys +
   объяснение разницы sandbox/production (тестовые вердикты vs реальные решения по
   реальным контрагентам — как у Alloy, это compliance-домен, ошибка стоит дорого).
2. **Форма** — environment select ДО ввода ключа (влияет на ожидаемый префикс) +
   api_key (password-type, с client-side проверкой префикса на соответствие
   выбранному environment).
3. **После успеха** — готовность сразу проверить любой бизнес (`create_business_
   verification`) — форма поиска/создания бизнеса должна быть первым CTA в центре,
   не спрятана в меню.
4. **Production warning** — явное предупреждение при первом переключении на production
   аналогично Alloy/Plaid.
5. **Ошибка "key/environment mismatch"** — если ключ mk_test_ используется с
   environment=production (или наоборот) — конкретное сообщение, не общая 401.

## 3. Разница с реализацией сейчас
См. `UI_COMPONENT_PLAN.md` §0.
