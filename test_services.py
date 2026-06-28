import unittest
import os
import json
from services.db_service import db_service
from services.image_service import ImageService
from services.pdf_service import PDFService
from services.ai_service import ai_service
from api.index import app

class TestKiraakStudy(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_db_service(self):
        # Verify SQLite DB initiates correctly and profiles can be queried
        profiles = db_service.query("SELECT * FROM profiles")
        self.assertIsNotNone(profiles)

    def test_image_enhancement(self):
        # Generate dummy 100x100 RGB image bytes
        from PIL import Image
        import io
        img = Image.new('RGB', (100, 100), color = 'red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        
        enhanced = ImageService.enhance_image(img_bytes.getvalue())
        self.assertIsNotNone(enhanced)
        self.assertTrue(len(enhanced) > 0)

    def test_ai_mock_fallback(self):
        # Verify AI fallback functions return mock structural payloads when API key is unset
        vision_res = ai_service.process_vision_document(b"dummy_bytes")
        self.assertEqual(vision_res["subject"], "Computer Science")
        
        materials = ai_service.generate_study_materials("Operating Systems")
        self.assertIn("notes", materials)
        self.assertIn("flashcards", materials)

    def test_routes_integrity(self):
        # Verify login route responds correctly
        response = self.app.get('/login')
        self.assertEqual(response.status_code, 200)

if __name__ == "__main__":
    unittest.main()
