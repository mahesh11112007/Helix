import json
import os
from collections import defaultdict

class SyllabusService:
    def __init__(self, data_dir="data/syllabus"):
        self.data_dir = data_dir

    def get_available_education_levels(self):
        """Returns list of education levels (e.g. ['intermediate', 'btech'])"""
        if not os.path.exists(self.data_dir):
            return []
        return [d for d in os.listdir(self.data_dir) if os.path.isdir(os.path.join(self.data_dir, d))]

    def get_available_boards(self, education_level):
        """Returns list of boards (e.g. ['tg', 'ap']) for an education level"""
        path = os.path.join(self.data_dir, education_level)
        if not os.path.exists(path):
            return []
        return [d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))]

    def get_available_years(self, education_level, board):
        """Returns list of JSON files (e.g. ['first_year', 'second_year'])"""
        path = os.path.join(self.data_dir, education_level, board)
        if not os.path.exists(path):
            return []
        files = [f for f in os.listdir(path) if f.endswith(".json")]
        return [f.replace(".json", "") for f in files]

    def get_syllabus_data(self, education_level, board, year):
        """Loads and returns the JSON syllabus data"""
        filepath = os.path.join(self.data_dir, education_level, board, f"{year}.json")
        if not os.path.exists(filepath):
            return None
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_available_groups(self, education_level, board, year):
        """Returns available groups/branches (e.g. ['MPC', 'BiPC'])"""
        data = self.get_syllabus_data(education_level, board, year)
        if not data or "groups" not in data:
            return []
        return list(data["groups"].keys())

    def get_subjects_for_group(self, education_level, board, year, group):
        """Returns subjects, chapters, and topics for a specific group"""
        data = self.get_syllabus_data(education_level, board, year)
        if not data or "groups" not in data or group not in data["groups"]:
            return []
        return data["groups"][group]

syllabus_service = SyllabusService()
