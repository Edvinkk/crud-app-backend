import unittest
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import models

with patch.object(models.Base.metadata, "create_all"):
    import main


class CsvImportTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        models.Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_import_quotes_unicode_and_duplicates(self):
        content = '\ufeffname,description\r\n Apple ,"Red, sweet fruit"\r\nApple,"Café\nfruit"\r\n'
        result = main.import_csv(content.encode("utf-8"), self.db)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].name, "Apple")
        self.assertEqual(result[0].description, "Red, sweet fruit")
        self.assertEqual(result[1].description, "Café\nfruit")
        self.assertNotEqual(result[0].id, result[1].id)
        with Session(self.engine) as saved:
            self.assertEqual(saved.query(models.Item).count(), 2)

    def test_blank_lines(self):
        result = main.import_csv(b"name,description\n\nPear,Fruit\n", self.db)
        self.assertEqual(result[0].name, "Pear")

    def test_invalid_files_leave_database_unchanged(self):
        self.db.add(models.Item(name="Existing", description="Keep me"))
        self.db.commit()
        for content in (
            b"", b"name,description\n", b"name,name\nA,B",
            b"name,description\nApple,Fruit\nPear,   ",
            b"name,description\nApple,Fruit\nPear",
            b"name,description\nApple,Fruit,Extra",
            b'name,description\nApple,"Unclosed',
            b"name,description\nApple,\xff",
        ):
            with self.subTest(content=content):
                with self.assertRaises(HTTPException) as error:
                    main.import_csv(content, self.db)
                self.assertEqual(error.exception.status_code, 400)
                self.assertEqual(self.db.query(models.Item).count(), 1)

    def test_database_failure_rolls_back(self):
        with patch.object(self.db, "commit", side_effect=RuntimeError("Test failure")):
            with self.assertRaises(RuntimeError):
                main.import_csv(b"name,description\nApple,Fruit", self.db)
        self.assertEqual(self.db.query(models.Item).count(), 0)


if __name__ == "__main__":
    unittest.main()
