import os
import io
import re
import requests
from PIL import Image, ImageDraw, ImageFont
from .. import loader, utils


@loader.tds
class SkalanizatorMod(loader.Module):
    """Добавляет текст на картинки"""

    strings = {
        "name": "Скаланизатор",
        "help": (
            "🪐 Module Скаланизатор loaded ( ･ω･)ﾉ\n"
            "ℹ️ Скаланизатор v1.1 — добавляет текст на картинки\n\n"
            "▫️ .j [номер (опц.)] [текст/реплай] — создать мем\n"
            "▫️ .jadd <ссылка> — добавить картинку\n"
            "▫️ .jclear — очистить список картинок\n"
            "▫️ .jdel <номер/диапазон> — удалить картинку\n"
            "▫️ .jlist — список картинок"
        ),
    }

    def __init__(self):
        self.config_path = "skalanizator_list.txt"
        self._ensure_file()

    def _ensure_file(self):
        if not os.path.exists(self.config_path):
            with open(self.config_path, "w") as f:
                f.write("")

    def _load_list(self):
        with open(self.config_path, "r") as f:
            return [line.strip() for line in f if line.strip()]

    def _save_list(self, items):
        with open(self.config_path, "w") as f:
            f.write("\n".join(items))

    async def jhelpcmd(self, message):
        """Показать помощь"""
        await utils.answer(message, self.strings["help"])

    async def jlistcmd(self, message):
        """Список картинок"""
        items = self._load_list()
        if not items:
            return await utils.answer(message, "📂 Список пуст")
        out = "📂 Список картинок:\n\n" + "\n".join(
            f"{i+1}. {url}" for i, url in enumerate(items)
        )
        await utils.answer(message, out)

    async def jaddcmd(self, message):
        """Добавить картинку"""
        args = utils.get_args_raw(message)
        if not args:
            return await utils.answer(message, "⚠️ Укажи ссылку")
        items = self._load_list()
        items.append(args)
        self._save_list(items)
        await utils.answer(message, f"✅ Добавлено (#{len(items)})")

    async def jclearcmd(self, message):
        """Очистить список"""
        self._save_list([])
        await utils.answer(message, "🧹 Список очищен")

    async def jdelcmd(self, message):
        """Удалить картинку по номеру или диапазону"""
        args = utils.get_args_raw(message)
        if not args:
            return await utils.answer(message, "⚠️ Укажи номер или диапазон")

        items = self._load_list()
        if "-" in args:
            try:
                start, end = map(int, args.split("-"))
                start, end = start - 1, end
                del items[start:end]
                self._save_list(items)
                return await utils.answer(message, f"🗑 Удалены картинки {args}")
            except:
                return await utils.answer(message, "⚠️ Неверный диапазон")
        else:
            try:
                idx = int(args) - 1
                removed = items.pop(idx)
                self._save_list(items)
                return await utils.answer(message, f"🗑 Удалена: {removed}")
            except:
                return await utils.answer(message, "⚠️ Неверный номер")

    async def jcmd(self, message):
        """Создать мем"""
        args = utils.get_args_raw(message).split(maxsplit=1)

        items = self._load_list()
        if not items:
            return await utils.answer(message, "📂 Список пуст")

        img_url = items[0]
        text = ""

        if args and args[0].isdigit():
            idx = int(args[0]) - 1
            if 0 <= idx < len(items):
                img_url = items[idx]
            if len(args) > 1:
                text = args[1]
        elif args:
            text = " ".join(args)

        if not text and message.is_reply:
            reply = await message.get_reply_message()
            text = reply.raw_text or ""

        if not text:
            return await utils.answer(message, "⚠️ Нет текста")

        try:
            img_bytes = requests.get(img_url, timeout=10).content
            img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        except Exception as e:
            return await utils.answer(message, f"🚫 Ошибка загрузки картинки: {e}")

        img = self._add_text(img, text)
        out = io.BytesIO()
        out.name = "meme.jpg"
        img.save(out, "JPEG")
        out.seek(0)

        await message.reply(file=out)

    def _add_text(self, img, text):
        draw = ImageDraw.Draw(img)
        font_size = max(20, img.width // 18)
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", font_size)
        except:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), text, font=font)
        text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]

        x = (img.width - text_width) // 2
        y = img.height - text_height - 10

        outline = 3
        for dx in range(-outline, outline + 1):
            for dy in range(-outline, outline + 1):
                if dx or dy:
                    draw.text((x + dx, y + dy), text, font=font, fill="black")
        draw.text((x, y), text, font=font, fill="white")

        return img