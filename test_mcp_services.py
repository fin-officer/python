#!/usr/bin/env python3

"""
Skrypt do testowania serweru00f3w MCP dla aplikacji Fin Officer
"""

import asyncio
import json
import sys
import httpx
from datetime import datetime

# Konfiguracja URL serweru00f3w MCP
MCP_EMAIL_URL = "http://localhost:8001/mcp/email"
MCP_SPAM_URL = "http://localhost:8002/mcp/spam"
MCP_ATTACHMENT_URL = "http://localhost:8003/mcp/attachments"

# Przyku0142adowe dane testowe
TEST_EMAIL = {
    "email_content": "Dzieu0144 dobry, jestem zainteresowany usu0142ugami ksiu0119gowymi. Czy mogu0142by Pan/Pani przesu0142au0107 mi informacje o cenach i pakietach? Potrzebuju0119 pomocy z rozliczeniem podatkowym mojej firmy.",
    "subject": "Zapytanie o usu0142ugi ksiu0119gowe",
    "sender_name": "Jan Kowalski",
    "sender_email": "jan.kowalski@example.com",
    "has_attachments": False
}

TEST_SPAM_LEGITIMATE = {
    "sender_email": "jan.kowalski@finofficer.com",
    "subject": "Prou015bba o spotkanie",
    "content": "Dzieu0144 dobry, chciau0142bym umu00f3wiu0107 siu0119 na spotkanie w sprawie usu0142ug ksiu0119gowych."
}

TEST_SPAM_SUSPICIOUS = {
    "sender_email": "unknown@suspicious-domain.xyz",
    "subject": "PILNE: Twoje konto wymaga weryfikacji",
    "content": "KLIKNIJ TUTAJ, aby zweryfikowau0107 swoje konto lub zostanie zawieszone! http://suspicious-link.xyz"
}

TEST_ATTACHMENT_VALID = {
    "filename": "dokument_testowy.pdf",
    "file_size": 1048576,  # 1MB
    "content_type": "application/pdf"
}

TEST_ATTACHMENT_INVALID = {
    "filename": "podejrzany.exe",
    "file_size": 1048576,  # 1MB
    "content_type": "application/x-msdownload"
}


async def test_mcp_server(url: str, name: str):
    """Testuje pou0142u0105czenie z serwerem MCP"""
    print(f"\nTestowanie serwera MCP: {name}")
    try:
        # Uu017cyjemy du0142uu017cszego timeoutu dla zapytau0144 HTTP
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Inicjalizacja sesji - najpierw pobieramy nagu0142u00f3wek mcp-session-id
            print(f"  Inicjalizacja sesji z {url}...")
            init_response = await client.get(url, headers={"Accept": "text/event-stream"})
            session_id = init_response.headers.get("mcp-session-id")
            
            print(f"  Odpowiedu017a: {init_response.status_code} - {init_response.headers}")
            
            if not session_id:
                print(f"\u274c Nie mou017cna uzyskau0107 identyfikatora sesji dla serwera {name}")
                # Spu00f3bujmy pobrau0107 sesju0119 w inny sposu00f3b
                print(f"  Pru00f3ba uzyskania sesji przez /resources...")
                resources_response = await client.get(f"{url}/resources", headers={"Accept": "text/event-stream"})
                session_id = resources_response.headers.get("mcp-session-id")
                
                if not session_id:
                    print(f"\u274c Nadal nie mou017cna uzyskau0107 identyfikatora sesji")
                    return False, None
                
            # Teraz pobieramy zasoby z poprawnym identyfikatorem sesji
            print(f"  Pobieranie zasobu00f3w z ID sesji: {session_id}...")
            response = await client.get(
                f"{url}/resources", 
                headers={
                    "Accept": "text/event-stream",
                    "mcp-session-id": session_id
                }
            )
            
            if response.status_code == 200:
                print(f"\u2705 Serwer {name} jest dostu0119pny (ID sesji: {session_id})")
                return True, session_id
            else:
                print(f"\u274c Serwer {name} zwru00f3ciu0142 kod bu0142u0119du: {response.status_code}")
                print(f"  Treu015bu0107 odpowiedzi: {response.text}")
                return False, None
    except httpx.ConnectError as e:
        print(f"\u274c Bu0142u0105d pou0142u0105czenia z serwerem {name}: {str(e)}")
        print(f"  Sprawdź, czy serwer {name} jest uruchomiony i dostępny pod adresem {url}")
        return False, None
    except httpx.TimeoutError as e:
        print(f"\u274c Timeout podczas u0142u0105czenia z serwerem {name}: {str(e)}")
        print(f"  Serwer {name} nie odpowiada w wyznaczonym czasie")
        return False, None
    except Exception as e:
        print(f"\u274c Bu0142u0105d podczas u0142u0105czenia z serwerem {name}: {str(e)}")
        import traceback
        print(f"  Szczegu00f3u0142y bu0142u0119du:
{traceback.format_exc()}")
        return False, None


async def test_email_analysis(session_id: str):
    """Testuje analizu0119 emaila"""
    print("\nTestowanie analizy emaila...")
    try:
        async with httpx.AsyncClient() as client:
            
            # Przygotowanie u017cu0105dania JSON-RPC
            json_rpc_request = {
                "jsonrpc": "2.0",
                "id": "test-email-analysis",
                "method": "analyze_email",
                "params": TEST_EMAIL
            }
            
            # Wywou0142anie narzu0119dzia MCP
            response = await client.post(
                f"{MCP_EMAIL_URL}/tools/analyze_email",
                headers={
                    "Accept": "text/event-stream",
                    "Content-Type": "application/json",
                    "mcp-session-id": session_id
                },
                json=json_rpc_request
            )
            
            if response.status_code == 200:
                print("\u2705 Analiza emaila zakou0144czona sukcesem")
                # Parsowanie odpowiedzi SSE
                for line in response.text.split("\n"):
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        if "result" in data:
                            print(f"Wynik analizy: {json.dumps(data['result'], indent=2, ensure_ascii=False)}")
                return True
            else:
                print(f"\u274c Analiza emaila zwru00f3ciu0142a kod bu0142u0119du: {response.status_code}")
                print(f"Treu015bu0107 odpowiedzi: {response.text}")
                return False
    except Exception as e:
        print(f"\u274c Bu0142u0105d podczas analizy emaila: {str(e)}")
        return False


async def test_spam_detection(session_id: str):
    """Testuje wykrywanie spamu"""
    print("\nTestowanie wykrywania spamu...")
    try:
        async with httpx.AsyncClient() as client:
            
            # Test legalnego emaila
            json_rpc_request_legitimate = {
                "jsonrpc": "2.0",
                "id": "test-spam-legitimate",
                "method": "detect_spam",
                "params": TEST_SPAM_LEGITIMATE
            }
            
            response_legitimate = await client.post(
                f"{MCP_SPAM_URL}/tools/detect_spam",
                headers={
                    "Accept": "text/event-stream",
                    "Content-Type": "application/json",
                    "mcp-session-id": session_id
                },
                json=json_rpc_request_legitimate
            )
            
            # Test podejrzanego emaila
            json_rpc_request_suspicious = {
                "jsonrpc": "2.0",
                "id": "test-spam-suspicious",
                "method": "detect_spam",
                "params": TEST_SPAM_SUSPICIOUS
            }
            
            response_suspicious = await client.post(
                f"{MCP_SPAM_URL}/tools/detect_spam",
                headers={
                    "Accept": "text/event-stream",
                    "Content-Type": "application/json",
                    "mcp-session-id": session_id
                },
                json=json_rpc_request_suspicious
            )
            
            if response_legitimate.status_code == 200 and response_suspicious.status_code == 200:
                print("\u2705 Wykrywanie spamu zakou0144czone sukcesem")
                # Parsowanie odpowiedzi dla legalnego emaila
                legitimate_result = None
                for line in response_legitimate.text.split("\n"):
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        if "result" in data:
                            legitimate_result = data["result"]
                
                # Parsowanie odpowiedzi dla podejrzanego emaila
                suspicious_result = None
                for line in response_suspicious.text.split("\n"):
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        if "result" in data:
                            suspicious_result = data["result"]
                
                if legitimate_result and suspicious_result:
                    print(f"Legalny email - wynik: {legitimate_result.get('is_spam', 'N/A')}")
                    print(f"Podejrzany email - wynik: {suspicious_result.get('is_spam', 'N/A')}")
                    return True
                else:
                    print("\u274c Nie mou017cna odczytau0107 wyniku00f3w detekcji spamu")
                    return False
            else:
                print(f"\u274c Wykrywanie spamu zwru00f3ciu0142o kod bu0142u0119du")
                return False
    except Exception as e:
        print(f"\u274c Bu0142u0105d podczas wykrywania spamu: {str(e)}")
        return False


async def test_attachment_validation(session_id: str):
    """Testuje walidacju0119 zau0142u0105czniku00f3w"""
    print("\nTestowanie walidacji zau0142u0105czniku00f3w...")
    try:
        async with httpx.AsyncClient() as client:
            
            # Test poprawnego zau0142u0105cznika
            json_rpc_request_valid = {
                "jsonrpc": "2.0",
                "id": "test-attachment-valid",
                "method": "validate_attachment",
                "params": TEST_ATTACHMENT_VALID
            }
            
            response_valid = await client.post(
                f"{MCP_ATTACHMENT_URL}/tools/validate_attachment",
                headers={
                    "Accept": "text/event-stream",
                    "Content-Type": "application/json",
                    "mcp-session-id": session_id
                },
                json=json_rpc_request_valid
            )
            
            # Test niepoprawnego zau0142u0105cznika
            json_rpc_request_invalid = {
                "jsonrpc": "2.0",
                "id": "test-attachment-invalid",
                "method": "validate_attachment",
                "params": TEST_ATTACHMENT_INVALID
            }
            
            response_invalid = await client.post(
                f"{MCP_ATTACHMENT_URL}/tools/validate_attachment",
                headers={
                    "Accept": "text/event-stream",
                    "Content-Type": "application/json",
                    "mcp-session-id": session_id
                },
                json=json_rpc_request_invalid
            )
            
            if response_valid.status_code == 200 and response_invalid.status_code == 200:
                print("\u2705 Walidacja zau0142u0105czniku00f3w zakou0144czona sukcesem")
                # Parsowanie odpowiedzi dla poprawnego zau0142u0105cznika
                valid_result = None
                for line in response_valid.text.split("\n"):
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        if "result" in data:
                            valid_result = data["result"]
                
                # Parsowanie odpowiedzi dla niepoprawnego zau0142u0105cznika
                invalid_result = None
                for line in response_invalid.text.split("\n"):
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        if "result" in data:
                            invalid_result = data["result"]
                
                if valid_result and invalid_result:
                    print(f"Poprawny zau0142u0105cznik - wynik: {valid_result.get('is_valid', 'N/A')}")
                    print(f"Niepoprawny zau0142u0105cznik - wynik: {invalid_result.get('is_valid', 'N/A')}")
                    return True
                else:
                    print("\u274c Nie mou017cna odczytau0107 wyniku00f3w walidacji zau0142u0105czniku00f3w")
                    return False
            else:
                print(f"\u274c Walidacja zau0142u0105czniku00f3w zwru00f3ciu0142a kod bu0142u0119du")
                return False
    except Exception as e:
        print(f"\u274c Bu0142u0105d podczas walidacji zau0142u0105czniku00f3w: {str(e)}")
        return False


async def test_auto_reply_generation(session_id: str):
    """Testuje generowanie auto-odpowiedzi"""
    print("\nTestowanie generowania auto-odpowiedzi...")
    try:
        async with httpx.AsyncClient() as client:
            
            # Przygotowanie u017cu0105dania JSON-RPC
            json_rpc_request = {
                "jsonrpc": "2.0",
                "id": "test-auto-reply",
                "method": "generate_auto_reply",
                "params": {
                    "email_content": TEST_EMAIL["email_content"],
                    "subject": TEST_EMAIL["subject"],
                    "sender_name": TEST_EMAIL["sender_name"],
                    "sender_email": TEST_EMAIL["sender_email"]
                }
            }
            
            # Wywou0142anie narzu0119dzia MCP
            response = await client.post(
                f"{MCP_EMAIL_URL}/tools/generate_auto_reply",
                headers={
                    "Accept": "text/event-stream",
                    "Content-Type": "application/json",
                    "mcp-session-id": session_id
                },
                json=json_rpc_request
            )
            
            if response.status_code == 200:
                print("\u2705 Generowanie auto-odpowiedzi zakou0144czone sukcesem")
                # Parsowanie odpowiedzi SSE
                for line in response.text.split("\n"):
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        if "result" in data:
                            result = data["result"]
                            print(f"Wygenerowana odpowiedu017a:\n{result.get('reply_content', 'N/A')}")
                            print(f"Szablon: {result.get('template_used', 'N/A')}")
                return True
            else:
                print(f"\u274c Generowanie auto-odpowiedzi zwru00f3ciu0142o kod bu0142u0119du: {response.status_code}")
                print(f"Treu015bu0107 odpowiedzi: {response.text}")
                return False
    except Exception as e:
        print(f"\u274c Bu0142u0105d podczas generowania auto-odpowiedzi: {str(e)}")
        return False


async def run_tests():
    """Uruchamia wszystkie testy"""
    print("\n=== Rozpoczynanie testu00f3w MCP dla Fin Officer ===\n")
    print(f"Data i czas: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Testowanie pou0142u0105czenia z serwerami MCP
    email_server_ok, email_session_id = await test_mcp_server(MCP_EMAIL_URL, "Email Processor")
    spam_server_ok, spam_session_id = await test_mcp_server(MCP_SPAM_URL, "Spam Detector")
    attachment_server_ok, attachment_session_id = await test_mcp_server(MCP_ATTACHMENT_URL, "Attachment Processor")
    
    results = []
    
    # Uruchamianie testu00f3w funkcjonalnych tylko jeu015bli serwery su0105 dostu0119pne
    if email_server_ok and email_session_id:
        # Przekazujemy identyfikator sesji do testu00f3w
        results.append(("Analiza emaila", await test_email_analysis(email_session_id)))
        results.append(("Generowanie auto-odpowiedzi", await test_auto_reply_generation(email_session_id)))
    
    if spam_server_ok and spam_session_id:
        # Przekazujemy identyfikator sesji do testu00f3w
        results.append(("Wykrywanie spamu", await test_spam_detection(spam_session_id)))
    
    if attachment_server_ok and attachment_session_id:
        # Przekazujemy identyfikator sesji do testu00f3w
        results.append(("Walidacja zau0142u0105czniku00f3w", await test_attachment_validation(attachment_session_id)))
    
    # Podsumowanie wyniku00f3w
    print("\n=== Podsumowanie testu00f3w ===\n")
    all_passed = True
    for name, result in results:
        status = "\u2705 PASSED" if result else "\u274c FAILED"
        print(f"{name}: {status}")
        if not result:
            all_passed = False
    
    print("\n=== Koniec testu00f3w ===\n")
    return all_passed


if __name__ == "__main__":
    try:
        result = asyncio.run(run_tests())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\nTesty przerwane przez uu017cytkownika")
        sys.exit(130)
