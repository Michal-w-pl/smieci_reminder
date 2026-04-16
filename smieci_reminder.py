#!/usr/bin/env python3
"""
Automatyczne przypomnienia o wywozi śmieci – ul. Kilińskiego, Radomsko
Źródło harmonogramów: PGK Radomsko (pgk-radomsko.pl)

Uruchomienie lokalne:   python smieci_reminder.py
Tryb testowy:           python smieci_reminder.py --test
Podgląd harmonogramu:   python smieci_reminder.py --lista
"""

import smtplib
import os
import sys
import json
import argparse
from datetime import date, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

# ══════════════════════════════════════════════════════
#  KONFIGURACJA
#  Lokalnie: plik config.json
#  GitHub Actions: zmienne środowiskowe (Secrets)
# ══════════════════════════════════════════════════════

def wczytaj_config():
    """Czyta config z env (GitHub Actions) lub config.json (lokalnie)."""

    # Jeśli ustawione zmienne środowiskowe – użyj ich (GitHub Actions)
    if os.environ.get("EMAIL_NADAWCY"):
        return {
            "email_nadawcy":   os.environ["EMAIL_NADAWCY"],
            "haslo_aplikacji": os.environ["HASLO_APLIKACJI"],
            "email_odbiorcy":  os.environ["EMAIL_ODBIORCY"],
            "dni_przed":       1,
            "typy_odpadow":    {"zmieszane": True, "worki": True, "bio": True},
        }

    # Lokalnie – czytaj z config.json
    config_path = Path(__file__).parent / "config.json"
    if not config_path.exists():
        domyslny = {
            "email_nadawcy":   "aimemw84@gmail.com",
            "haslo_aplikacji": "xxxx xxxx xxxx xxxx",
            "email_odbiorcy":  "aimemw84@gmail.com",
            "dni_przed":       1,
            "typy_odpadow":    {"zmieszane": True, "worki": True, "bio": True},
        }
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(domyslny, f, indent=2, ensure_ascii=False)
        print(f"✅ Utworzono config.json – uzupełnij hasło aplikacji Gmail!")
        sys.exit(1)

    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


# ══════════════════════════════════════════════════════
#  HARMONOGRAM 2025 + 2026 – ul. Kilińskiego, Radomsko
#  Rejon I/Nr1 (zmieszane), Rejon V/Nr5 (worki), Rejon IX/Nr3 (bio)
# ══════════════════════════════════════════════════════

HARMONOGRAM = {
    "zmieszane": [
        # 2025
        date(2025,1,13), date(2025,2,10), date(2025,3,10),
        date(2025,4,7),  date(2025,4,18),
        date(2025,5,5),  date(2025,5,19),
        date(2025,6,2),  date(2025,6,16), date(2025,6,30),
        date(2025,7,14), date(2025,7,28),
        date(2025,8,11), date(2025,8,25),
        date(2025,9,8),  date(2025,9,22),
        date(2025,10,6), date(2025,10,20),
        date(2025,11,10),date(2025,12,8),
        # 2026
        date(2026,1,12), date(2026,2,9),  date(2026,3,9),
        date(2026,4,3),  date(2026,4,20),
        date(2026,5,4),  date(2026,5,18),
        date(2026,6,1),  date(2026,6,15), date(2026,6,29),
        date(2026,7,13), date(2026,7,27),
        date(2026,8,10), date(2026,8,24),
        date(2026,9,7),  date(2026,9,21),
        date(2026,10,5), date(2026,10,19),
        date(2026,11,9), date(2026,12,7),
    ],
    "worki": [
        # 2025
        date(2025,1,9),  date(2025,2,7),  date(2025,3,7),
        date(2025,4,7),  date(2025,5,9),  date(2025,6,6),
        date(2025,7,7),  date(2025,8,7),  date(2025,9,5),
        date(2025,10,7), date(2025,11,7), date(2025,12,5),
        # 2026
        date(2026,1,9),  date(2026,2,6),  date(2026,3,6),
        date(2026,4,8),  date(2026,5,8),  date(2026,6,8),
        date(2026,7,7),  date(2026,8,7),  date(2026,9,7),
        date(2026,10,7), date(2026,11,6), date(2026,12,7),
    ],
    "bio": [
        # 2025
        date(2025,1,8),  date(2025,2,5),  date(2025,3,5),
        date(2025,4,2),  date(2025,4,16), date(2025,4,30),
        date(2025,5,14), date(2025,5,28),
        date(2025,6,11), date(2025,6,25),
        date(2025,7,9),  date(2025,7,23),
        date(2025,8,6),  date(2025,8,20),
        date(2025,9,3),  date(2025,9,17),
        date(2025,10,1), date(2025,10,15),date(2025,10,29),
        date(2025,11,19),date(2025,12,17),
        # 2026
        date(2026,1,7),  date(2026,2,4),  date(2026,3,4),
        date(2026,4,1),  date(2026,4,15), date(2026,4,29),
        date(2026,5,13), date(2026,5,27),
        date(2026,6,10), date(2026,6,24),
        date(2026,7,8),  date(2026,7,22),
        date(2026,8,5),  date(2026,8,19),
        date(2026,9,2),  date(2026,9,16), date(2026,9,30),
        date(2026,10,14),date(2026,10,28),
        date(2026,11,18),date(2026,12,16),
    ],
}

NAZWY_TYPOW = {
    "zmieszane": "⬜ Odpady zmieszane (pojemnik)",
    "worki":     "🟡 Worki – papier, szkło, plastik",
    "bio":       "🟤 Bioodpady i odpady zielone",
}

DNI_TYGODNIA = ["Poniedziałek","Wtorek","Środa","Czwartek","Piątek","Sobota","Niedziela"]
MIESIĄCE     = ["","Stycznia","Lutego","Marca","Kwietnia","Maja","Czerwca",
                "Lipca","Sierpnia","Września","Października","Listopada","Grudnia"]


# ══════════════════════════════════════════════════════
#  LOGIKA
# ══════════════════════════════════════════════════════

def znajdz_wywozy_na_date(target_date, typy_aktywne):
    wyniki = {}
    for typ, daty in HARMONOGRAM.items():
        if typy_aktywne.get(typ, True) and target_date in daty:
            wyniki[typ] = True
    return wyniki


def najbliższe_wywozy(dni=30):
    dziś = date.today()
    wyniki = {}
    for i in range(dni):
        d = dziś + timedelta(days=i)
        for typ, daty in HARMONOGRAM.items():
            if d in daty:
                wyniki.setdefault(d, []).append(typ)
    return sorted(wyniki.items())


def formatuj_date(d):
    return f"{DNI_TYGODNIA[d.weekday()]}, {d.day} {MIESIĄCE[d.month]} {d.year}"


def buduj_html(wywozy_typy, dni_przed, target_date):
    typy_html = "".join(
        f'<li style="margin:6px 0;font-size:15px;">{NAZWY_TYPOW[t]}</li>'
        for t in wywozy_typy
    )

    if dni_przed == 1:
        alert_html = """
        <div style="background:#fff3cd;border:2px solid #ffc107;border-radius:8px;
                    padding:14px 18px;margin:20px 0;font-size:15px;color:#664d03;">
          ⚠️ <strong>JUTRO WYWÓZ!</strong><br>
          Wystaw pojemniki dziś wieczór – muszą stać przed posesją przed godz. 6:00 rano.
        </div>"""
    else:
        alert_html = f"""
        <div style="background:#d1ecf1;border:2px solid #bee5eb;border-radius:8px;
                    padding:14px 18px;margin:20px 0;font-size:15px;color:#0c5460;">
          ℹ️ Za <strong>{dni_przed} dni</strong> planowany wywóz.
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="pl">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:20px;background:#f0ece0;font-family:Arial,sans-serif;">
  <div style="max-width:500px;margin:0 auto;background:#fff;border-radius:12px;
              padding:28px;border:1px solid #ddd;box-shadow:0 2px 8px rgba(0,0,0,0.08);">

    <div style="border-bottom:2px solid #f0ece0;padding-bottom:16px;margin-bottom:20px;">
      <h2 style="margin:0 0 4px;font-size:20px;color:#1a1a1a;">♻️ Wywóz śmieci</h2>
      <p style="margin:0;color:#888;font-size:13px;">ul. Kilińskiego · Radomsko · PGK Radomsko</p>
    </div>

    {alert_html}

    <p style="font-size:15px;margin:0 0 12px;">
      <strong>📅 Data wywozu:</strong><br>
      <span style="font-size:17px;color:#333;">{formatuj_date(target_date)}</span>
    </p>

    <p style="font-size:13px;color:#666;margin:16px 0 6px;text-transform:uppercase;
              letter-spacing:0.05em;">Rodzaj odpadów:</p>
    <ul style="margin:0 0 24px;padding-left:18px;">
      {typy_html}
    </ul>

    <div style="background:#f9f7f2;border-radius:8px;padding:12px 16px;font-size:12px;color:#999;">
      Źródło: PGK Radomsko · pgk-radomsko.pl<br>
      Powiadomienie automatyczne – nie odpowiadaj na tego maila.
    </div>
  </div>
</body>
</html>"""


def wyslij_mail(config, temat, html):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = temat
    msg["From"]    = config["email_nadawcy"]
    msg["To"]      = config["email_odbiorcy"]
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as srv:
            srv.login(config["email_nadawcy"], config["haslo_aplikacji"])
            srv.sendmail(config["email_nadawcy"], config["email_odbiorcy"], msg.as_bytes())
        print(f"✅ Mail wysłany → {config['email_odbiorcy']}")
        return True
    except smtplib.SMTPAuthenticationError:
        print("❌ Błąd autoryzacji – sprawdź hasło aplikacji Gmail!")
        print("   https://myaccount.google.com/apppasswords")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Błąd SMTP: {e}")
        sys.exit(1)


def sprawdz_i_wyslij(config, dni_przed, tryb_testowy=False):
    dziś = date.today()
    typy_aktywne = config.get("typy_odpadow", {})

    if tryb_testowy:
        # użyj najbliższego wywozu zamiast jutrzejszego
        nadchodzące = najbliższe_wywozy(60)
        if not nadchodzące:
            print("❌ Brak wywozów w harmonogramie w ciągu 60 dni.")
            return
        target, typy_list = nadchodzące[0]
        wywozy = {t: True for t in typy_list if typy_aktywne.get(t, True)}
        dni_przed = (target - dziś).days
        print(f"🔍 Tryb testowy – używam najbliższego wywozu: {formatuj_date(target)}")
    else:
        target = dziś + timedelta(days=dni_przed)
        wywozy = znajdz_wywozy_na_date(target, typy_aktywne)

    if not wywozy:
        print(f"ℹ️  {formatuj_date(target)} – brak wywozu. Mail nie zostanie wysłany.")
        return

    typy_naz = [NAZWY_TYPOW[t] for t in wywozy]
    print(f"🗓️  Wywóz {formatuj_date(target)}: {', '.join(t.split(' ',1)[1] for t in typy_naz)}")

    if dni_przed == 1:
        temat = f"⚠️ Jutro wywóz śmieci – {target.day} {MIESIĄCE[target.month]}"
    else:
        temat = f"🗓️ Wywóz śmieci za {dni_przed} dni – {target.day} {MIESIĄCE[target.month]}"

    wyslij_mail(config, temat, buduj_html(list(wywozy.keys()), dni_przed, target))


def pokaz_liste():
    nadchodzące = najbliższe_wywozy(30)
    print("\n📋 Najbliższe wywozy (30 dni):\n")
    if not nadchodzące:
        print("   Brak wywozów.")
        return
    for d, typy in nadchodzące:
        delta = (d - date.today()).days
        if delta == 0:   prefix = "  DZIŚ  "
        elif delta == 1: prefix = "  JUTRO "
        else:            prefix = f"  za {delta:2d}d "
        print(f"{prefix}  {formatuj_date(d):<38}  {', '.join(typy)}")
    print()


# ══════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Przypomnienia o wywozi śmieci – ul. Kilińskiego, Radomsko")
    parser.add_argument("--test",  action="store_true", help="Wyślij testowy mail (najbliższy wywóz)")
    parser.add_argument("--days",  type=int,            help="Sprawdź za N dni (domyślnie z config)")
    parser.add_argument("--lista", action="store_true", help="Pokaż harmonogram bez wysyłania")
    args = parser.parse_args()

    if args.lista:
        pokaz_liste()
        return

    config   = wczytaj_config()
    dni      = args.days if args.days is not None else config.get("dni_przed", 1)
    sprawdz_i_wyslij(config, dni, tryb_testowy=args.test)


if __name__ == "__main__":
    main()
