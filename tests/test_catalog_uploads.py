from io import BytesIO

from PIL import Image

from app import catalog
from db_case import PostgresCase
from test_login_integration import csrf, request


def upload(path, cookies, data, **fields):
    boundary = "catalog-test-boundary"
    parts = [
        f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
        for name, value in fields.items()
    ]
    parts.append(
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="upload"\r\n\r\n'.encode()
        + data + f"\r\n--{boundary}--\r\n".encode()
    )
    return request(path, cookies, multipart=(f"multipart/form-data; boundary={boundary}".encode(), b"".join(parts)))


class CatalogUploadsTest(PostgresCase):
    def test_import_rollback_and_photo_lifecycle(self):
        self.master = {**self.master, "locale": "pt"}
        path = "/catalog/import"
        token = csrf(request(path, self.master)[2])
        self.assertEqual(request(path)[0], 303)
        self.assertEqual(request(path + "/template", self.reader)[0], 403)
        self.assertIn(b"code,description", request(path + "/template", self.master)[2])
        self.assertIn(b"Importar productos", request(path, {**self.master, "locale": "es"})[2])
        data = b"\xef\xbb\xbfcode;description;barcode\r\n001;Produto;000123\r\n"
        self.assertEqual(upload(path, self.reader, data, csrf=token)[0], 403)
        self.assertEqual(upload(path, self.master, data, csrf="invalid")[0], 403)
        self.assertEqual(upload(path, self.master, b"x" * (1024 * 1024 + 1), csrf=token)[0], 400)
        self.assertEqual(upload(path, self.master, data, csrf=token)[0], 200)
        sku = catalog.list_skus(True, "")[0]
        self.assertEqual((sku["code"], sku["barcode"]), ("001", "000123"))
        duplicate = b"code,description,barcode\nNEW,Temporary,\nOTHER,Duplicate,000123\n"
        status, _, body = upload(path, self.master, duplicate, csrf=token)
        self.assertEqual(status, 409)
        self.assertIn(b"Linha 3.", body)
        self.assertEqual(len(catalog.list_skus(True, "")), 1)

        photo_path = f'/catalog/{sku["id"]}/image'
        output = BytesIO()
        Image.new("RGBA", (1200, 600), "red").save(output, "PNG")
        fields = {"csrf": token, "version": sku["version"]}
        self.assertEqual(upload(photo_path, self.master, b"<svg/>", **fields)[0], 400)
        self.assertEqual(upload(photo_path, self.reader, output.getvalue(), **fields)[0], 403)
        self.assertEqual(upload(photo_path, self.master, output.getvalue(), **fields)[0], 303)
        self.assertEqual(upload(photo_path, self.master, output.getvalue(), **fields)[0], 409)
        self.assertEqual(request(photo_path)[0], 303)
        status, headers, body = request(photo_path, self.reader)
        self.assertEqual(status, 200)
        self.assertEqual(dict(headers)[b"content-type"], b"image/jpeg")
        with Image.open(BytesIO(body)) as image:
            self.assertEqual(image.size, (960, 480))
        replacement = BytesIO()
        Image.new("RGB", (40, 30), "blue").save(replacement, "JPEG")
        fields["version"] += 1
        self.assertEqual(upload(photo_path, self.master, replacement.getvalue(), **fields)[0], 303)
        with Image.open(BytesIO(request(photo_path, self.reader)[2])) as image:
            self.assertEqual(image.size, (40, 30))
        catalog.deactivate_sku(self.actor_id, sku["id"])
        self.assertEqual(request(photo_path, self.reader)[0], 404)
        self.assertEqual(request(photo_path, self.master)[0], 200)
        fields["version"] += 2
        self.assertEqual(request(photo_path + "/remove", self.master, fields)[0], 303)
        self.assertEqual(request(photo_path, self.master)[0], 404)
        with self.isolated_connection() as connection:
            events = connection.execute("SELECT action FROM catalog_audit ORDER BY id").fetchall()
        self.assertEqual(events, [("created",), ("edited",), ("edited",), ("deactivated",), ("edited",)])
