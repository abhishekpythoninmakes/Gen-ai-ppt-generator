"""Comprehensive API test script for AI PPT Generator."""
import httpx
import json
import sys

BASE = "http://127.0.0.1:8000"
PASS = 0
FAIL = 0

def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name} — {detail}")

def main():
    global PASS, FAIL
    client = httpx.Client(base_url=BASE, timeout=30)

    # ─── 1. Health Check ─────────────────────────────
    print("\n🔹 1. Health Check")
    r = client.get("/api/health")
    test("GET /api/health returns 200", r.status_code == 200)
    test("Response has status=healthy", r.json().get("status") == "healthy")

    # ─── 2. Registration ─────────────────────────────
    print("\n🔹 2. Registration")

    # Valid registration  
    r = client.post("/api/auth/register", json={
        "email": "apitest@example.com",
        "username": "apitestuser",
        "password": "StrongPass1"
    })
    test("Valid registration returns 200", r.status_code == 200)
    data = r.json()
    test("Response has access_token", "access_token" in data)
    test("Response has user object", "user" in data)
    test("User has correct email", data.get("user", {}).get("email") == "apitest@example.com")
    test("Token type is bearer", data.get("token_type") == "bearer")
    
    # Duplicate email
    r = client.post("/api/auth/register", json={
        "email": "apitest@example.com",
        "username": "another",
        "password": "StrongPass1"
    })
    test("Duplicate email returns 400", r.status_code == 400, f"got {r.status_code}")
    test("Error message mentions email", "email" in r.json().get("detail", "").lower(), r.json().get("detail"))

    # Duplicate username
    r = client.post("/api/auth/register", json={
        "email": "unique@example.com",
        "username": "apitestuser",
        "password": "StrongPass1"
    })
    test("Duplicate username returns 400", r.status_code == 400, f"got {r.status_code}")

    # Weak password
    r = client.post("/api/auth/register", json={
        "email": "weak@example.com",
        "username": "weakuser",
        "password": "weak"
    })
    test("Weak password returns 422", r.status_code == 422, f"got {r.status_code}")

    # Invalid email
    r = client.post("/api/auth/register", json={
        "email": "not-an-email",
        "username": "invalidemail",
        "password": "StrongPass1"
    })
    test("Invalid email returns 422", r.status_code == 422, f"got {r.status_code}")

    # ─── 3. Login ─────────────────────────────────────
    print("\n🔹 3. Login")

    # Login with email
    r = client.post("/api/auth/login", json={
        "identifier": "apitest@example.com",
        "password": "StrongPass1"
    })
    test("Login with email returns 200", r.status_code == 200)
    token = r.json().get("access_token", "")
    test("Login returns token", len(token) > 0)

    # Login with username
    r = client.post("/api/auth/login", json={
        "identifier": "apitestuser",
        "password": "StrongPass1"
    })
    test("Login with username returns 200", r.status_code == 200)
    token = r.json().get("access_token", "")
    headers = {"Authorization": f"Bearer {token}"}

    # Wrong credentials
    r = client.post("/api/auth/login", json={
        "identifier": "apitestuser",
        "password": "WrongPassword1"
    })
    test("Wrong password returns 401", r.status_code == 401, f"got {r.status_code}")
    test("Error says invalid credentials", "invalid" in r.json().get("detail", "").lower())

    # Non-existent user
    r = client.post("/api/auth/login", json={
        "identifier": "nonexistent",
        "password": "StrongPass1"
    })
    test("Non-existent user returns 401", r.status_code == 401)

    # ─── 4. Auth /me ──────────────────────────────────
    print("\n🔹 4. Auth /me")
    r = client.get("/api/auth/me", headers=headers)
    test("GET /me with valid token returns 200", r.status_code == 200)
    test("Returns correct username", r.json().get("username") == "apitestuser")

    # Invalid token
    r = client.get("/api/auth/me", headers={"Authorization": "Bearer invalidtoken"})
    test("Invalid JWT returns 401", r.status_code == 401)

    # No token
    r = client.get("/api/auth/me")
    test("No token returns 403", r.status_code == 403, f"got {r.status_code}")

    # ─── 5. Settings ─────────────────────────────────
    print("\n🔹 5. Settings")
    r = client.get("/api/settings", headers=headers)
    test("GET /settings returns 200", r.status_code == 200)
    sdata = r.json()
    test("Has groq_api_key field", "groq_api_key" in sdata)
    test("Has pexels_api_key field", "pexels_api_key" in sdata)
    test("Has unsplash_access_key field", "unsplash_access_key" in sdata)
    test("Has unsplash_secret_key field", "unsplash_secret_key" in sdata)
    test("No pixabay field", "pixabay_api_key" not in sdata)

    # Update settings
    r = client.post("/api/settings", headers=headers, json={
        "groq_api_key": "groq_test_key_for_local_api_checks_only",
        "pexels_api_key": "pexels_test_key_for_local_api_checks_only",
        "unsplash_access_key": "unsplash_access_1234567890",
        "unsplash_secret_key": "unsplash_secret_1234567890",
    })
    test("POST /settings returns 200", r.status_code == 200)
    sdata = r.json()
    test("Groq key is masked", "•" in sdata.get("groq_api_key", ""))
    test("Pexels key is masked", "•" in sdata.get("pexels_api_key", ""))
    test("Unsplash access key is masked", "•" in sdata.get("unsplash_access_key", ""))

    # Masked keys should NOT overwrite stored keys
    r = client.post("/api/settings", headers=headers, json=sdata)
    test("Sending masked keys back doesn't corrupt stored keys", r.status_code == 200)
    sdata2 = r.json()
    test("Keys still masked after re-save", "•" in sdata2.get("groq_api_key", ""))

    # ─── 6. Blank PPT ────────────────────────────────
    print("\n🔹 6. Blank PPT Creation")
    r = client.post("/api/ppt/blank", headers=headers)
    test("POST /ppt/blank returns 200", r.status_code == 200)
    ppt = r.json()
    ppt_id = ppt.get("id")
    test("PPT has id", ppt_id is not None)
    test("PPT has title", ppt.get("title") == "Untitled Presentation")
    test("PPT has content_json", "content_json" in ppt)
    
    # Validate content_json structure
    content = json.loads(ppt["content_json"])
    test("Content has title field", "title" in content)
    test("Content has slides array", isinstance(content.get("slides"), list))
    test("Has at least 1 slide", len(content.get("slides", [])) >= 1)
    first_slide = content["slides"][0]
    test("Slide has heading", "heading" in first_slide)
    test("Slide has points array", isinstance(first_slide.get("points"), list))
    test("Slide has description", "description" in first_slide)

    # ─── 7. PPT List ─────────────────────────────────
    print("\n🔹 7. PPT List")
    r = client.get("/api/ppt/list", headers=headers)
    test("GET /ppt/list returns 200", r.status_code == 200)
    ppts = r.json()
    test("Returns a list", isinstance(ppts, list))
    test("Has at least 1 PPT", len(ppts) >= 1)

    # ─── 8. Get single PPT ───────────────────────────
    print("\n🔹 8. Get Single PPT")
    r = client.get(f"/api/ppt/{ppt_id}", headers=headers)
    test("GET /ppt/{id} returns 200", r.status_code == 200)
    test("Returns correct PPT", r.json().get("id") == ppt_id)

    # Non-existent PPT
    r = client.get("/api/ppt/99999", headers=headers)
    test("Non-existent PPT returns 404", r.status_code == 404)

    # ─── 9. Update PPT ───────────────────────────────
    print("\n🔹 9. Update PPT")
    new_content = json.dumps({"title": "Updated Title", "theme": "dark", "slides": content["slides"]})
    r = client.put(f"/api/ppt/{ppt_id}", headers=headers, json={
        "title": "Updated Title",
        "content_json": new_content
    })
    test("PUT /ppt/{id} returns 200", r.status_code == 200)
    test("Title updated", r.json().get("title") == "Updated Title")

    # Invalid JSON
    r = client.put(f"/api/ppt/{ppt_id}", headers=headers, json={
        "content_json": "not valid json{{"
    })
    test("Invalid JSON returns 400", r.status_code == 400, f"got {r.status_code}")

    # ─── 10. Delete PPT ──────────────────────────────
    print("\n🔹 10. Delete PPT")
    r = client.delete(f"/api/ppt/{ppt_id}", headers=headers)
    test("DELETE /ppt/{id} returns 200", r.status_code == 200)

    # Confirm deleted
    r = client.get(f"/api/ppt/{ppt_id}", headers=headers)
    test("Deleted PPT returns 404", r.status_code == 404)

    # ─── 11. Edge Cases ──────────────────────────────
    print("\n🔹 11. Edge Cases")

    # Empty prompt
    r = client.post("/api/ppt/generate", headers=headers, json={
        "prompt": "",
        "num_slides": 6
    })
    test("Empty prompt returns 400", r.status_code == 400, f"got {r.status_code}")

    # Very long prompt 
    r = client.post("/api/ppt/generate", headers=headers, json={
        "prompt": "A" * 6000,
        "num_slides": 6
    })
    test("Very long prompt returns 400", r.status_code == 400, f"got {r.status_code}")

    # ─── 12. Export ──────────────────────────────────
    print("\n🔹 12. Export")
    # Create a PPT first to export
    r = client.post("/api/ppt/blank", headers=headers)
    export_ppt_id = r.json()["id"]
    r = client.get(f"/api/export/{export_ppt_id}/pptx", headers=headers)
    test("Export PPTX returns 200", r.status_code == 200)
    test("Content-Type is pptx", "presentationml" in r.headers.get("content-type", ""))
    test("Has Content-Disposition header", "content-disposition" in r.headers)
    test("File is non-empty", len(r.content) > 0)

    # Cleanup
    client.delete(f"/api/ppt/{export_ppt_id}", headers=headers)

    # ─── Summary ─────────────────────────────────────
    print(f"\n{'='*50}")
    print(f"  ✅ PASSED: {PASS}")
    print(f"  ❌ FAILED: {FAIL}")
    print(f"  TOTAL:    {PASS + FAIL}")
    print(f"{'='*50}")
    
    if FAIL > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
