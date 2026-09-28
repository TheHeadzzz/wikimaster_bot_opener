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
    """Détecte et coche la case Captcha / Turnstile, même si elle se trouve dans un iframe."""
    iframe = page.frame_locator('iframe[src*="cloudflare"], iframe[src*="turnstile"]')
    case_iframe = iframe.get_by_role("checkbox", name="Vérifiez que vous êtes humain")
    case_page = page.get_by_role("checkbox", name="Vérifiez que vous êtes humain")

    try:
        page.wait_for_selector('iframe[src*="cloudflare"], input[type="checkbox"]', timeout=3000)
    except PlaywrightTimeout:
        return

    try:
        if case_iframe.is_visible(timeout=1000):
            case_iframe.click()
            print("Captcha coché (iframe)")
            page.wait_for_timeout(2000)
            return
    except Exception:
        pass

    try:
        if case_page.is_visible(timeout=1000):
            page.locator("label", has=case_page).click()
            print("Captcha coché (page)")
            page.wait_for_timeout(2000)
            return
    except Exception:
        pass


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
        bouton_booster.wait_for(state="visible", timeout=30000)
    
        # Flèche "suivant"
        bouton_suivant = page.locator("button:has(polyline[points='9 18 15 12 9 6'])")
        bouton_continuer = page.get_by_role("button", name="Continuer")
        
        # Si le bouton est cliquable (actif)
        if bouton_booster.is_enabled():
            print("Booster disponible ! Ouverture...")
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