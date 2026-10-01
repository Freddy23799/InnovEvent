"""Coordonnées de l'entreprise utilisées sur tous les documents PDF officiels
(billets, reçus, attestations, fiches de paie). À remplacer par les informations
juridiques réelles d'InnovEvent avant mise en production (RCCM, NIU, adresse
définitive, etc.)."""

import os

COMPANY_NAME = "InnovEvent-GS"
COMPANY_ADDRESS = "Avenue Kennedy, Yaoundé, Cameroun"
COMPANY_PHONE = "+237 6XX XXX XXX"
COMPANY_EMAIL = "contact@innovevent.example"
COMPANY_WEBSITE = "www.innovevent.example"

LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "logo.png")
