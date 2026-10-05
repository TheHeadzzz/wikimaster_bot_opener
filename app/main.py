from camoufox.sync_api import Camoufox
from playwright.sync_api import expect, TimeoutError as PlaywrightTimeout
import os
import time

EMAIL = os.environ.get("MY_APP_EMAIL")
PASSWORD = os.environ.get("MY_APP_PASSWORD")

if not EMAIL or not PASSWORD:
    raise ValueError("Les variables d'identification doivent être définies.")

URL_LOGIN = "https://www.wiki-masters.com/login"
URL_ACCUEIL = "https://www.wiki-masters.com/"  # URL principale après connexion
NB_CLICS_CARTES = 4
MARGE_SECONDES = 2  

def gerer_captcha(page):
    """Calcule la position de la case à cocher proportionnellement au div turnstile et clique dessus."""
    selecteur_div = 'div[id^="turnstile-"]'
    try:
        div_element = page.wait_for_selector(selecteur_div, timeout=10000)
        if div_element and div_element.is_visible():
            box = div_element.bounding_box()
            if box:
                clic_x = box["x"] + (box["width"] * 0.09)
                clic_y = box["y"] + (box["height"] * 0.50)
                page.mouse.click(clic_x, clic_y)
                print(f"Clic Turnstile effectué aux coordonnées ({clic_x:.1f}, {clic_y:.1f})")
                page.wait_for_timeout(2000)
                return True
    except Exception as e:
        print(f"Info captcha : Aucun captcha détecté ({type(e).__name__})")
    return False

def handle_bot_detection(page):
    try:
        checkbox = page.wait_for_locator("xpath=//div[contains(., 'Vérification rapide')]//input[@type='checkbox']", timeout=5000)
        checkbox.check()
        bouton_continuer = page.wait_for_locator(
            "xpath=//div[contains(., 'Vérification rapide')]//button[contains(., 'Continuer')]", timeout=5000)
        bouton_continuer.click()
    except Exception as e:
        print(f"Erreur mineure lors du contournement bot : {e}")

def lire_attente_en_secondes(page):
    """Lit le texte du span dans le div 'Prochain dans ...' et le convertit en secondes."""
    try:
        span = page.get_by_text("Prochain dans").locator("span")
        span.wait_for(state="visible", timeout=10000)
        texte = span.inner_text().strip()  

        if "Prêt" in texte:
            return 0

        secondes = 0
        for partie in texte.split(":"):
            secondes = secondes * 60 + int(partie)
        return secondes
    except Exception as e:
        print(f"Impossible de lire le temps d'attente ({e}), nouvelle tentative par défaut dans 60s.")
        return 60

# --- LANCEMENT UNIQUE DU NAVIGATEUR (Il reste ouvert en arrière-plan) ---
print("Démarrage de Camoufox...")
with Camoufox(headless=False, os=["windows", "macos"], humanize=True) as navigateur:
    page = navigateur.new_page()

    # --- Connexion initiale unique ---
    try:
        print("Première connexion...")
        page.goto(URL_LOGIN, timeout=60000)
        gerer_captcha(page)
        
        page.locator("#email").fill(EMAIL)
        page.locator("#password").fill(PASSWORD)
        page.get_by_role("button", name="Connexion").click()
        
        page.wait_for_load_state("networkidle", timeout=30000)
        print("Connecté avec succès !")
    except Exception as e:
        print(f"Erreur critique lors de la connexion initiale : {e}")
        # Si la connexion initiale échoue, on s'arrête là pour laisser l'humain regarder
        exit(1)

    # --- BOUCLE PRINCIPALE DE REPRISE SANS FERMER LE NAVIGATEUR ---
    while True:
        try:
            # Si on est tombé sur une page d'erreur ou déconnecté, on retourne sur l'accueil
            if "/login" in page.url:
                print("⚠️ Redirection détectée vers le login. Tentative de reconnexion automatique...")
                page.locator("#email").fill(EMAIL)
                page.locator("#password").fill(PASSWORD)
                page.get_by_role("button", name="Connexion").click()
                page.wait_for_load_state("networkidle", timeout=30000)

            # Le bouton du booster spécifique aux paquets
            bouton_booster = page.get_by_role("button", name="Ouvrir un paquet")
            
            try:
                bouton_booster.wait_for(state="visible", timeout=15000)
            except PlaywrightTimeout:
                print("Booster non visible, tentative de contournement...")
                handle_bot_detection(page)
                try:
                    bouton_booster.wait_for(state="visible", timeout=5000)
                except PlaywrightTimeout:
                    print("🔄 Élément introuvable, actualisation de la page d'accueil pour repartir sur du propre...")
                    page.goto(URL_ACCUEIL, timeout=30000)
                    continue

            bouton_suivant = page.locator("button:has(polyline[points='9 18 15 12 9 6'])")
            bouton_continuer = page.get_by_role("button", name="Continuer")
            
            if bouton_booster.is_enabled():
                print("Ouverture d'un booster !")
                gerer_captcha(page)
                bouton_booster.click()
                gerer_captcha(page)

                for _ in range(NB_CLICS_CARTES):
                    try:
                        bouton_suivant.click(timeout=3000)
                        page.wait_for_timeout(500)
                    except Exception:
                        break 

                try:
                    bouton_continuer.click(timeout=5000)
                except Exception:
                    pass
                    
                page.wait_for_timeout(1000)
            else:
                attente = lire_attente_en_secondes(page)
                print(f"Prochain booster dans {attente} secondes")
                delai_total = max(attente + MARGE_SECONDES, 5)
                page.wait_for_timeout(delai_total * 1000)

        except Exception as loop_err:
            print(f"⚠️ Erreur rencontrée dans la boucle : {loop_err}")
            print("Récupération en cours : rechargement de la page d'accueil dans 5 secondes...")
            time.sleep(5)
            try:
                page.goto(URL_ACCUEIL, timeout=30000)
            except Exception:
                print("Impossible de recharger la page, nouvelle tentative au prochain tour...")
