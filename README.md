# Email LLM Processor - Python + FastAPI + FastMCP

Minimalistyczna aplikacja do przetwarzania wiadomości e-mail z wykorzystaniem modeli językowych (LLM) napisana w Pythonie z użyciem FastAPI i FastMCP. System umożliwia automatyczne przetwarzanie, analizę i generowanie odpowiedzi na wiadomości e-mail przy użyciu zaawansowanych modeli językowych.

## Funkcjonalności

- Odbieranie i wysyłanie wiadomości e-mail
- Integracja z modelami językowymi (LLM) do analizy i generowania odpowiedzi
- Zaawansowany system szablonów odpowiedzi
- Archiwizacja wiadomości
- Śledzenie historii komunikacji z nadawcami
- REST API do zarządzania wiadomościami i szablonami
- Dokumentacja API w Swagger
- Automatyczne przetwarzanie w tle

## Wymagania

- Python 3.9 lub nowszy
- Docker i Docker Compose (dla łatwego uruchomienia)
- Ansible 2.9 lub nowszy (dla testów automatycznych)
  ```bash
  # Instalacja Ansible na Ubuntu/Debian
  sudo apt update
  sudo apt install ansible
  
  # Instalacja Ansible na CentOS/RHEL
  sudo yum install epel-release
  sudo yum install ansible
  
  # Instalacja Ansible przez pip
  pip install ansible

## Szybki Start

1. Sklonuj repozytorium:
   ```bash
   git clone https://github.com/yourusername/email-llm-processor-python.git
   cd email-llm-processor-python
   ```

2. Zainstaluj wymagane zależności:
   ```bash
   ./scripts/install.sh
   ```
   Skrypt automatycznie zainstaluje Docker, Docker Compose, Ansible i wszystkie wymagane zależności Python.

3. Uruchom aplikację:
   ```bash
   ./run-python.sh
   ```

4. Przetestuj system:
   ```bash
   ./test-python.sh urgent
   ```

5. Uruchom testy Ansible (opcjonalnie):
   ```bash
   ./ansible/run
   ```

4. Otwórz interfejs API w przeglądarce:
   http://localhost:8000/docs

## Struktura Projektu

```
email-llm-processor-python/
├── app/
│   ├── main.py                     # Główny punkt wejścia FastAPI
│   ├── models.py                   # Modele danych Pydantic
│   ├── services/
│   │   ├── email_service.py        # Usługa do obsługi email
│   │   ├── llm_service.py          # Usługa do komunikacji z LLM
│   │   ├── template_service.py     # Usługa szablonów odpowiedzi
│   │   └── db_service.py           # Usługa bazy danych
│   └── processors/
│       └── email_processor.py      # Logika przetwarzania emaili
├── ansible/                        # Testy Ansible
│   ├── main.yml                    # Główny playbook testowy
│   ├── email_tests.yml             # Testy podstawowej funkcjonalności email
│   ├── email_service_tests.yml     # Testy usługi email
│   ├── email_scenarios_tests.yml   # Testy różnych scenariuszy email
│   ├── inventory.ini               # Plik inwentarza Ansible
│   ├── ansible.cfg                 # Konfiguracja Ansible
│   └── run_tests.sh                # Skrypt do uruchamiania testów
├── docker-compose.yml              # Konfiguracja Docker Compose
├── Dockerfile                      # Definicja obrazu Docker
├── requirements.txt                # Zależności Pythona
├── run-python.sh                   # Skrypt uruchomieniowy
└── test-python.sh                  # Skrypt testowy
```

## Zalety Implementacji w Python + FastAPI

### Minimalna ilość kodu

Dzięki zastosowaniu Pythona z FastAPI oraz dekoratorów Pydantic, uzyskaliśmy niezwykle zwięzłą i czytelną implementację:

- **Automatyczna walidacja danych wejściowych** - modele Pydantic zapewniają walidację bez dodatkowego kodu
- **Asynchroniczne przetwarzanie** - natywna obsługa async/await
- **Dekoratory dla powtarzalnych zadań** - `@repeat_every` dla cyklicznych zadań
- **FastMCP** dla szybkiej integracji z modelami językowymi

### Łatwość rozszerzania

Dzięki modułowej strukturze, łatwo można rozszerzyć funkcjonalność:

1. **Dodanie nowego endpointu API**:

```python
@app.post("/api/some-feature")
async def new_feature(data: YourModel):
    # Implementacja
    return {"result": "success"}
```

2. **Dodanie nowego szablonu odpowiedzi**:

Wystarczy utworzyć plik `nazwa.template` w katalogu `/data/templates/`

### Integracja z LLM

Implementacja używa wyspecjalizowanej klasy `LlmService` do komunikacji z modelami językowymi:

```python
async def analyze_tone(self, content: str) -> ToneAnalysis:
    prompt = self._create_analysis_prompt(content)
    response = await self._call_llm_api(prompt)
    return self._parse_analysis_response(response)
```

## API REST

FastAPI automatycznie generuje dokumentację Swagger dostępną pod adresem http://localhost:8000/docs

### Główne Endpointy:

- **POST /api/emails/process** - Ręczne przetwarzanie wiadomości
- **POST /api/emails/{email_id}/reply** - Odpowiadanie na wiadomość email
- **POST /api/emails/{email_id}/auto-reply** - Automatyczne odpowiadanie na wiadomość email z użyciem MCP
- **POST /api/emails/fetch** - Ręczne pobieranie wiadomości email
- **GET /api/templates** - Pobieranie listy dostępnych szablonów
- **GET /api/templates/{key}** - Pobieranie konkretnego szablonu
- **GET /health** - Sprawdzenie stanu aplikacji
- **POST /api/emails/send-test** - Wysłanie testowej wiadomości

## Automatyczne odpowiedzi z użyciem MCP

System obsługuje automatyczne generowanie odpowiedzi na wiadomości email przy użyciu protokołu MCP (Model Context Protocol) dla modelu TinyLLM z Ollama. Funkcjonalność ta pozwala na:

1. **Inteligentne odpowiedzi**: System analizuje treść wiadomości i generuje odpowiednie odpowiedzi
2. **Kontekstowe zrozumienie**: Wykorzystuje historię konwersacji do tworzenia spójnych odpowiedzi
3. **Personalizacja**: Dostosowuje ton i treść odpowiedzi do nadawcy

Aby użyć funkcji automatycznej odpowiedzi, wywołaj endpoint:

```
POST /api/emails/{email_id}/auto-reply
```

System pobierze wiadomość, wygeneruje odpowiedź przy użyciu MCP i wyśle ją do nadawcy.

## Testowanie

Projekt zawiera kompleksowy framework do testowania i zapewnienia jakości kodu. Szczegółowe informacje znajdują się w pliku [TESTING.md](TESTING.md).

Główne narzędzia testowe:

- **Tox**: Do uruchamiania testów w izolowanych środowiskach
- **Pytest**: Do testów jednostkowych
- **Black**: Do formatowania kodu
- **Flake8/Pylint**: Do analizy statycznej kodu
- **GitHub Actions**: Do ciągłej integracji

Aby uruchomić wszystkie testy:

```bash
tox
```

## Dostosowanie Systemu

### Dodawanie nowych funkcjonalności

1. **Nowy analizator wiadomości**:
   - Dodaj nową metodę w klasie `LlmService`
   - Rozszerz model `ToneAnalysis` w `models.py`

2. **Nowy typ szablonu odpowiedzi**:
   - Dodaj plik w katalogu `/data/templates/`
   - Rozszerz metodę `select_template_key` w `template_service.py`

## Porównanie z Apache Camel

W porównaniu do implementacji z Apache Camel, wersja Python+FastAPI oferuje:

- **~70% mniej kodu** - implementacja tych samych funkcjonalności
- **Automatyczną dokumentację API** - bez dodatkowego kodu
- **Łatwiejszą integrację z LLM** - dzięki natywnej obsłudze JSON w Pythonie
- **Szybszy czas rozwoju** - dzięki idiomatycznemu podejściu Pythona
- **Brak zewnętrznych plików konfiguracyjnych** - w przeciwieństwie do XML w Camel

## Uruchamianie i Testowanie

### Uruchomienie 

```bash
./run-python.sh
```

### Testowanie

```bash
./test-python.sh [frequent|negative|urgent|new]
```

Gdzie:
- `frequent` - Testuje szablon dla częstych nadawców
- `negative` - Testuje szablon dla powtarzających się negatywnych opinii
- `urgent` - Testuje szablon dla pilnych wiadomości
- `new` - Testuje szablon dla nowych użytkowników

## Licencja

MIT