from camoufox.sync_api import Camoufox
from playwright.sync_api import expect, TimeoutError as PlaywrightTimeout
import os

EMAIL = os.environ.get("MY_APP_EMAIL")
PASSWORD = os.environ.get("MY_APP_PASSWORD")

if not EMAIL or not PASSWORD:
    raise ValueError("Les variables MY_APP_EMAIL et MY_APP_PASSWORD doivent être définies.")

# Utilisation dans Camoufox...

URL_LOGIN = "https://www.wiki-masters.com/login"


NB_CLICS_CARTES = 4
MARGE_SECONDES = 2  # petite marge ajoutée à l'attente

def gerer_captcha(page):
    """Calcule la position de la case à cocher proportionnellement au div turnstile et clique dessus."""
    # Sélecteur ciblant le div parent du Turnstile (qui commence par turnstile-)
    selecteur_div = 'div[id^="turnstile-"]'

    try:
        # 1. Attendre que le div conteneur soit visible
        div_element = page.wait_for_selector(selecteur_div, timeout=50000)

        if div_element and div_element.is_visible():
            box = div_element.bounding_box()

            if box:
                # 2. Calcul des coordonnées proportionnelles
                # La case est située à ~9% sur la largeur (ex: ~27px pour 300px)
                # et à 50% sur la hauteur
                clic_x = box["x"] + (box["width"] * 0.09)
                clic_y = box["y"] + (box["height"] * 0.50)

                # 3. Effectuer le clic physique via la souris
                page.mouse.click(clic_x, clic_y)
                print(f"Clic Turnstile effectué aux coordonnées ({clic_x:.1f}, {clic_y:.1f})")
                page.wait_for_timeout(2000)
                return True

    except Exception as e:
        print(f"Pas de captcha ou erreur lors du ciblage du div : {e}")

    return False

def handle_bot_detection(page):
    try:
        checkbox = page.wait_for_locator("xpath=//div[contains(., 'Vérification rapide')]//input[@type='checkbox']", timeout=5000)
        checkbox.check()
        bouton_continuer = page.wait_for_locator(
            "xpath=//div[contains(., 'Vérification rapide')]//button[contains(., 'Continuer')]", timeout=5000)
        bouton_continuer.click()
    except Exception as e:
        print(e)


def lire_attente_en_secondes(page):
    """Lit le texte du span dans le div 'Prochain dans ...' (ex: '1:41') et le convertit en secondes."""
    span = page.get_by_text("Prochain dans").locator("span")
    span.wait_for(state="visible", timeout=10000)
    texte = span.inner_text().strip()  # ex: "1:41", "1:02:03" ou "Prêt !"

    # Si le texte indique que c'est prêt, pas besoin de compter
    if "Prêt" in texte:
        return 0

    try:
        secondes = 0
        for partie in texte.split(":"):
            secondes = secondes * 60 + int(partie)
        return secondes
    except ValueError:
        return 0

# Camoufox agit comme le contexte de navigateur Playwright
with Camoufox(headless=False, os=["windows", "macos"], humanize=True) as navigateur:
    print("Starting...")
    page = navigateur.new_page()

    # --- Connexion ---
    page.goto(URL_LOGIN)
    gerer_captcha(page)
    print("Connexion...")
    page.locator("#email").fill(EMAIL)
    page.locator("#password").fill(PASSWORD)

    page.get_by_role("button", name="Connexion").click()

    print("Connecté !")
    # --- Boucle principale ---
    while True:
        # Le bouton du booster spécifique aux paquets
        bouton_booster = page.get_by_role("button", name="Ouvrir un paquet")
        try:
            bouton_booster.wait_for(state="visible", timeout=30000)
            print("Booster disponible...")
        except PlaywrightTimeout:
            print("Contournement du captcha..")
            handle_bot_detection(page)
            bouton_booster.wait_for(state="visible", timeout=1000)
            print("Contourné !")
        # Flèche "suivant"
        bouton_suivant = page.locator("button:has(polyline[points='9 18 15 12 9 6'])")
        bouton_continuer = page.get_by_role("button", name="Continuer")
        
        # Si le bouton est cliquable (actif)
        if bouton_booster.is_enabled():
            print("Ouverture d'un booster !")
            gerer_captcha(page)
            bouton_booster.click()
            gerer_captcha(page)

            for _ in range(NB_CLICS_CARTES):
                bouton_suivant.click()
                page.wait_for_timeout(500)  # laisse l'animation se terminer

            bouton_continuer.click()
            page.wait_for_timeout(1000)  # courte pause pour laisser le temps au bouton de repasser en disabled

        # Le bouton est désactivé (<button disabled>) : ON LIT LE TEMPS ET ON ATTEND
        else:
            attente = lire_attente_en_secondes(page)
            print(f"Prochain booster dans {attente} secondes")
            page.wait_for_timeout((attente + MARGE_SECONDES*10) * 1000)