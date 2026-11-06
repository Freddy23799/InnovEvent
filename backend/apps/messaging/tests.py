from django.test import SimpleTestCase

from .autoresponder import HANDOFF_REPLY, answer_support_message


class AutoresponderTests(SimpleTestCase):
    def reply(self, text, role=None):
        return answer_support_message(text, role=role)

    def test_small_talk_gets_short_answers_without_handoff(self):
        for text in ("Bonjour", "salut ça va ?", "merci beaucoup", "ok", "d'accord", "au revoir"):
            reply, handoff = self.reply(text)
            self.assertFalse(handoff, text)
            self.assertLess(len(reply), 60, text)
        self.assertTrue(self.reply("bonsoir")[0].startswith("Bonsoir"))

    def test_topics_point_to_the_right_place(self):
        cases = {
            "Bonjour, je veux louer 200 chaises pour 2 jours": "Louer",
            "je veux acheter des verres": "Boutique",
            "où est ma facture ?": "Mes commandes",
            "je cherche un DJ": "Marketplace des acteurs",
            "je cherche une salle pour 300 personnes": "Salles",
            "mot de passe oublié": "Mot de passe oublié",
            "code parrain": "Parrainage",
        }
        for text, expected in cases.items():
            reply, handoff = self.reply(text)
            self.assertIn(expected, reply, text)
            self.assertFalse(handoff, text)

    def test_answers_depend_on_account_type(self):
        self.assertIn("Demandes de devis reçues", self.reply("un devis", "partner")[0])
        self.assertIn("Demander un devis", self.reply("un devis", "client")[0])
        self.assertIn("CNI", self.reply("faire vérifier mon compte", "partner")[0])

    def test_unknown_questions_and_requests_for_a_human_are_handed_off(self):
        for text in ("quelle est la couleur du ciel", "je veux parler à un conseiller", "le site ne marche pas", "je veux annuler ma commande"):
            reply, handoff = self.reply(text)
            self.assertTrue(handoff, text)
        self.assertEqual(self.reply("quelle est la couleur du ciel")[0], HANDOFF_REPLY)


class PushSubscriptionTests(SimpleTestCase):
    def test_webpush_is_skipped_without_vapid_keys(self):
        from django.test import override_settings

        from apps.notifications import webpush

        with override_settings(WEBPUSH_VAPID_PUBLIC_KEY="", WEBPUSH_VAPID_PRIVATE_KEY=""):
            self.assertFalse(webpush.is_configured())
