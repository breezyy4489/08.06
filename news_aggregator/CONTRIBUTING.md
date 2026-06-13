# Руководство по Git-workflow для команды

## Стратегия веток

```
main                  ← production (только через merge)
├── feature/scraper   ← Backend Developer
├── feature/classifier ← ML Engineer
└── feature/flask-ui  ← Fullstack Developer
```

## Пошаговый workflow

### 1. Начало работы (каждый участник)

```bash
# Клонировать репозиторий
git clone https://github.com/<org>/news_aggregator.git
cd news_aggregator

# Создать свою ветку (не работать в main!)
git checkout -b feature/<твоя-роль>
# Примеры:
#   git checkout -b feature/scraper
#   git checkout -b feature/classifier
#   git checkout -b feature/flask-ui
```

### 2. Работа и коммиты

```bash
# Стадировать изменения
git add <файл>         # конкретный файл
git add .             # все изменения

# Коммит с понятным сообщением
git commit -m "feat: добавлен RSS-парсер для Lenta.ru"
git commit -m "fix: исправлена обработка пустого description"
git commit -m "docs: добавлен docstring в classify_article()"
```

**Формат сообщений коммитов:**
- `feat:` — новая функциональность
- `fix:` — исправление бага
- `docs:` — документация
- `refactor:` — рефакторинг без изменения поведения
- `test:` — тесты

### 3. Отправить ветку на GitHub

```bash
git push origin feature/<твоя-роль>
```

### 4. Создать Pull Request

1. Открыть GitHub → вкладка **Pull Requests**
2. Нажать **New Pull Request**
3. Base: `main` ← Compare: `feature/<твоя-роль>`
4. Добавить описание изменений
5. Назначить reviewer из команды

### 5. Тимлид — финальное слияние

```bash
# Убедиться что main актуален
git checkout main
git pull origin main

# Слить ветку backend
git merge feature/scraper
# Разрешить конфликты если есть, затем:
git add . && git commit -m "merge: feature/scraper → main"

# Слить ветку ML
git merge feature/classifier
git add . && git commit -m "merge: feature/classifier → main"

# Слить ветку Fullstack
git merge feature/flask-ui
git add . && git commit -m "merge: feature/flask-ui → main"

# Отправить в GitHub
git push origin main
```

### 6. Запуск финального проекта

```bash
# На машине тимлида после слияния всех веток
git checkout main
git pull origin main
pip install -r requirements.txt
python app.py
# Открыть http://127.0.0.1:5000
```

## Разрешение конфликтов

Если при merge возник конфликт:

```bash
# Git покажет конфликтующие файлы
git status

# Открыть файл, найти маркеры:
# <<<<<<< HEAD
# (ваш код)
# =======
# (входящий код)
# >>>>>>> feature/...

# Отредактировать файл, убрать маркеры
# Затем:
git add <файл>
git commit -m "fix: разрешён конфликт в <файл>"
```

## Правила

- ❌ Никогда не пушить напрямую в `main`
- ✅ Каждая задача — отдельная ветка
- ✅ Коммиты небольшие и понятные
- ✅ Перед merge обязательно `git pull origin main`
- ✅ Проверить что `python app.py` запускается после merge
