#!/usr/bin/env python3
"""
TELEGRAM USERBOT JASEBKING - COMPLETE SOURCE CODE
Version: 2.0 FULL FEATURED
Support: All media types, emoji premium, text formatting
Author: Jasebking
Creator : By @hiyaok

CARA PAKAI:
1. Ganti API_ID dan API_HASH di bawah
2. Install: pip install telethon
3. Run: python hiyaok.py
"""

import asyncio
import os
import json
import re
from datetime import datetime, time
from telethon import TelegramClient, events, functions, types
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError, UserNotParticipantError
from telethon.tl.types import MessageEntityCustomEmoji
from telethon.tl.custom import Message
import logging

# ==================== CONFIGURATION ====================
# GANTI DENGAN API CREDENTIALS ANDA DARI https://my.telegram.org
API_ID = 20706311  # GANTI DENGAN API ID ANDA (ANGKA)
API_HASH = '3bde90bb1545d10b9d2f302586ca5e6f'  # GANTI DENGAN API HASH ANDA

# File untuk menyimpan data
DATA_FILE = 'userbot_data.json'

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== MAIN USERBOT CLASS ====================
class UserBot:
    def __init__(self):
        self.client = None
        self.data = self.load_data()
        self.running = False
        self.timer_task = None
        
    def load_data(self):
        """Load saved data from JSON file"""
        default_data = {
            'admins': [],
            'groups': [],
            'selected_groups': [],
            'message': {'text': '', 'forward': False},
            'pm_enabled': False,
            'pm_message': '',
            'sleep_enabled': False,
            'sleep_time': {'start': '22:00', 'end': '06:00'},
            'notif_user': None,
            'spam_timer': 5,
            'group_timer': 1,
            'run_timer': None,
            'bot_active': True
        }
        
        try:
            if os.path.exists(DATA_FILE):
                with open(DATA_FILE, 'r') as f:
                    loaded_data = json.load(f)
                    for key, value in default_data.items():
                        if key not in loaded_data:
                            loaded_data[key] = value
                    return loaded_data
            return default_data
        except:
            return default_data
    
    def save_data(self):
        """Save data to JSON file"""
        with open(DATA_FILE, 'w') as f:
            json.dump(self.data, f, indent=2)
    
    async def start(self):
        """Start the userbot"""
        print("🤖 TELEGRAM USERBOT JASEBKING 🤖")
        print("=" * 50)
        print("📌 Version: 2.0 FULL FEATURED")
        print("📸 Support: All media, emoji premium, formatting")
        print("=" * 50)
        
        # Check session
        if not os.path.exists('userbot.session'):
            phone = input("\n📱 Masukkan nomor telepon (dengan kode negara, contoh: +628xxx): ")
            self.client = TelegramClient('userbot', API_ID, API_HASH)
        else:
            self.client = TelegramClient('userbot', API_ID, API_HASH)
        
        try:
            await self.client.start()
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("\n💡 Solusi:")
            print("1. Cek API_ID dan API_HASH sudah benar")
            print("2. Cek koneksi internet")
            print("3. Hapus file userbot.session dan coba lagi")
            return
        
        # Get self info
        me = await self.client.get_me()
        if not self.data['admins']:
            self.data['admins'] = [me.id]
            self.save_data()
        
        print(f"\n✅ Berhasil login sebagai: {me.first_name} (@{me.username})")
        print("=" * 50)
        
        # Register handlers
        self.register_handlers()
        
        # Send startup notification
        await self.send_admin_notif(
            "🚀 **USERBOT STARTED**\n\n"
            f"👤 **User:** {me.first_name}\n"
            f"🆔 **ID:** `{me.id}`\n"
            f"📱 **Username:** @{me.username}\n"
            f"⏰ **Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            "Ketik `.fitur` untuk melihat semua fitur."
        )
        
        print("\n📌 Bot berhasil dijalankan!")
        print("📌 Ketik .fitur di Telegram untuk melihat semua perintah")
        print("📌 Ketik .jasebking untuk tutorial")
        
        await self.client.run_until_disconnected()
    
    def register_handlers(self):
        """Register all event handlers"""
        
        @self.client.on(events.NewMessage(pattern=r'^\.jasebking$'))
        async def tutorial_handler(event):
            if not await self.is_admin(event.sender_id):
                return
            
            tutorial = """
🔑 **TUTORIAL USERBOT JASEBKING**

📋 **Cara Menggunakan:**
1. Cek grup yang ada: `.cekgrub`
2. Pilih grup: `.setgrub 2 5 8` atau `.setgrub all`
3. Reply pesan yang mau dikirim
4. Set pesan: `.pesan nofw` atau `.pesan fw`
5. Mulai kirim: `.run 5` (tiap 5 menit)
6. Stop: `.run off`

✨ **Support:**
• Semua jenis media (foto, video, dokumen, dll)
• Emoji premium & text formatting
• Caption dengan format bold, italic, dll

📚 Ketik `.fitur` untuk lihat semua perintah
"""
            await event.reply(tutorial)
        
        @self.client.on(events.NewMessage(pattern=r'^\.cekgrub$'))
        async def check_groups_handler(event):
            if not await self.is_admin(event.sender_id):
                return
            
            await event.reply("🔍 Mengecek grup...")
            
            self.data['groups'] = []
            index = 1
            
            message = "📁 **DAFTAR GRUP:**\n\n"
            
            async for dialog in self.client.iter_dialogs():
                if dialog.is_group or dialog.is_channel:
                    self.data['groups'].append({
                        'id': dialog.id,
                        'title': dialog.title,
                        'index': index
                    })
                    
                    status = "✅" if dialog.id in [g['id'] for g in self.data.get('selected_groups', [])] else "❌"
                    message += f"{index}. {status} **{dialog.title}**\n"
                    index += 1
            
            self.save_data()
            
            message += f"\n📊 Total: {len(self.data['groups'])} grup"
            await event.reply(message)
        
        @self.client.on(events.NewMessage(pattern=r'^\.setgrub\s+(.+)$'))
        async def set_groups_handler(event):
            if not await self.is_admin(event.sender_id):
                return
            
            args = event.pattern_match.group(1).strip()
            
            if args.lower() == 'all':
                self.data['selected_groups'] = self.data['groups'].copy()
                await event.reply(f"✅ Semua {len(self.data['groups'])} grup telah dipilih!")
            else:
                try:
                    indices = [int(x.strip()) for x in args.split()]
                    selected = []
                    
                    for idx in indices:
                        for group in self.data['groups']:
                            if group['index'] == idx:
                                selected.append(group)
                                break
                    
                    self.data['selected_groups'] = selected
                    await event.reply(f"✅ {len(selected)} grup telah dipilih!")
                except:
                    await event.reply("❌ Format salah! Gunakan: `.setgrub 1 2 3` atau `.setgrub all`")
            
            self.save_data()
        
        @self.client.on(events.NewMessage(pattern=r'^\.pesan\s+(fw|nofw)$'))
        async def set_message_handler(event):
            if not await self.is_admin(event.sender_id):
                return
            
            if not event.is_reply:
                await event.reply("❌ Reply ke pesan yang ingin disimpan!")
                return
            
            replied = await event.get_reply_message()
            forward = event.pattern_match.group(1) == 'fw'
            
            # Detect media type
            media_type = None
            if replied.photo:
                media_type = "Photo"
            elif replied.video:
                media_type = "Video"
            elif replied.document:
                media_type = "Document"
            elif replied.sticker:
                media_type = "Sticker"
            elif replied.voice:
                media_type = "Voice"
            elif replied.audio:
                media_type = "Audio"
            elif replied.gif:
                media_type = "GIF"
            
            # Save complete message data
            self.data['message'] = {
                'text': replied.text or '',
                'forward': forward,
                'from_id': replied.sender_id,
                'message_id': replied.id,
                'chat_id': replied.chat_id,
                'media_type': media_type,
                'has_media': bool(replied.media)
            }
            self.save_data()
            
            response = f"✅ Pesan berhasil disimpan!\n"
            response += f"📋 Mode: {'Forward' if forward else 'No Forward'}\n"
            if media_type:
                response += f"📎 Media: {media_type}\n"
            if replied.text:
                response += f"💬 Caption: Yes\n"
            response += f"✨ Emoji & formatting: **Preserved!**"
            
            await event.reply(response)
        
        @self.client.on(events.NewMessage(pattern=r'^\.on$'))
        async def activate_bot_handler(event):
            if not await self.is_admin(event.sender_id):
                return
            
            self.data['bot_active'] = True
            self.save_data()
            await event.reply("✅ Bot diaktifkan!")
        
        @self.client.on(events.NewMessage(pattern=r'^\.off$'))
        async def deactivate_bot_handler(event):
            if not await self.is_admin(event.sender_id):
                return
            
            self.data['bot_active'] = False
            self.running = False
            if self.timer_task:
                self.timer_task.cancel()
            self.save_data()
            await event.reply("❌ Bot dinonaktifkan!")
        
        @self.client.on(events.NewMessage(pattern=r'^\.pm\s+(.+)$'))
        async def pm_handler(event):
            if not await self.is_admin(event.sender_id):
                return
            
            args = event.pattern_match.group(1).strip()
            
            if args == 'on':
                self.data['pm_enabled'] = True
                await event.reply("✅ Auto reply PM diaktifkan!")
            elif args == 'off':
                self.data['pm_enabled'] = False
                await event.reply("❌ Auto reply PM dinonaktifkan!")
            else:
                self.data['pm_message'] = args
                await event.reply("✅ Pesan PM berhasil diatur!")
            
            self.save_data()
        
        @self.client.on(events.NewMessage(pattern=r'^\.tidur\s+(.+)$'))
        async def sleep_handler(event):
            if not await self.is_admin(event.sender_id):
                return
            
            args = event.pattern_match.group(1).strip()
            
            if args == 'on':
                self.data['sleep_enabled'] = True
                await event.reply("✅ Mode tidur diaktifkan!")
            elif args == 'off':
                self.data['sleep_enabled'] = False
                await event.reply("❌ Mode tidur dinonaktifkan!")
            else:
                match = re.match(r'(\d{1,2}[:.]\d{2})-(\d{1,2}[:.]\d{2})', args)
                if match:
                    self.data['sleep_time'] = {
                        'start': match.group(1).replace('.', ':'),
                        'end': match.group(2).replace('.', ':')
                    }
                    await event.reply(f"✅ Waktu tidur diatur: {match.group(1)} - {match.group(2)}")
                else:
                    await event.reply("❌ Format salah! Gunakan: `.tidur 22:00-06:00`")
            
            self.save_data()
        
        @self.client.on(events.NewMessage(pattern=r'^\.run\s+(.+)$'))
        async def run_handler(event):
            if not await self.is_admin(event.sender_id):
                return
            
            args = event.pattern_match.group(1).strip()
            
            if args == 'off':
                self.running = False
                if self.timer_task:
                    self.timer_task.cancel()
                self.data['run_timer'] = None
                await event.reply("⏹ Timer dihentikan!")
            else:
                try:
                    minutes = int(args)
                    self.data['run_timer'] = minutes
                    self.running = True
                    
                    await event.reply(f"▶️ Mulai mengirim pesan setiap {minutes} menit...")
                    
                    if self.timer_task:
                        self.timer_task.cancel()
                    self.timer_task = asyncio.create_task(self.timer_loop())
                except:
                    await event.reply("❌ Format salah! Gunakan: `.run 5` (dalam menit)")
            
            self.save_data()
        
        @self.client.on(events.NewMessage(pattern=r'^\.notif\s+(.+)$'))
        async def notif_handler(event):
            if not await self.is_admin(event.sender_id):
                return
            
            args = event.pattern_match.group(1).strip()
            
            if args == 'off':
                self.data['notif_user'] = None
                await event.reply("📴 Notifikasi dinonaktifkan!")
            else:
                self.data['notif_user'] = args.replace('@', '')
                await event.reply(f"📬 Notifikasi akan dikirim ke @{self.data['notif_user']}")
            
            self.save_data()
        
        @self.client.on(events.NewMessage(pattern=r'^\.timer\s+(spam|grub)\s+(\d+)$'))
        async def timer_handler(event):
            if not await self.is_admin(event.sender_id):
                return
            
            timer_type = event.pattern_match.group(1)
            seconds = int(event.pattern_match.group(2))
            
            if timer_type == 'spam':
                self.data['spam_timer'] = seconds
                await event.reply(f"⏱ Timer spam diatur: {seconds} detik")
            else:
                self.data['group_timer'] = seconds
                await event.reply(f"⏱ Timer antar grup diatur: {seconds} detik")
            
            self.save_data()
        
        @self.client.on(events.NewMessage(pattern=r'^\.admin\s+(add|del)\s+(.+)$'))
        async def admin_handler(event):
            if not await self.is_admin(event.sender_id):
                return
            
            action = event.pattern_match.group(1)
            username = event.pattern_match.group(2).replace('@', '')
            
            try:
                user = await self.client.get_entity(username)
                
                if action == 'add':
                    if user.id not in self.data['admins']:
                        self.data['admins'].append(user.id)
                        await event.reply(f"✅ {user.first_name} ditambahkan sebagai admin!")
                    else:
                        await event.reply("⚠️ User sudah menjadi admin!")
                else:
                    if user.id in self.data['admins'] and user.id != event.sender_id:
                        self.data['admins'].remove(user.id)
                        await event.reply(f"✅ {user.first_name} dihapus dari admin!")
                    else:
                        await event.reply("⚠️ Tidak dapat menghapus admin ini!")
                
                self.save_data()
            except:
                await event.reply("❌ User tidak ditemukan!")
        
        @self.client.on(events.NewMessage(pattern=r'^\.join\s+(.+)$'))
        async def join_handler(event):
            if not await self.is_admin(event.sender_id):
                return
            
            groups = event.pattern_match.group(1).split()
            joined = 0
            
            await event.reply(f"🔄 Mencoba join {len(groups)} grup...")
            
            for group in groups[:5]:
                try:
                    group_username = group.replace('@', '')
                    await self.client(functions.channels.JoinChannelRequest(group_username))
                    joined += 1
                    await asyncio.sleep(2)
                except Exception as e:
                    logger.error(f"Failed to join {group}: {e}")
            
            await event.reply(f"✅ Berhasil join {joined}/{len(groups[:5])} grup!")
        
        @self.client.on(events.NewMessage(pattern=r'^\.out$'))
        async def leave_all_handler(event):
            if not await self.is_admin(event.sender_id):
                return
            
            await event.reply("🔄 Keluar dari semua grup...")
            left = 0
            
            async for dialog in self.client.iter_dialogs():
                if dialog.is_group or dialog.is_channel:
                    try:
                        await self.client.delete_dialog(dialog)
                        left += 1
                        await asyncio.sleep(1)
                    except:
                        pass
            
            await event.reply(f"✅ Berhasil keluar dari {left} grup!")
        
        @self.client.on(events.NewMessage(pattern=r'^\.reset\s+all$'))
        async def reset_handler(event):
            if not await self.is_admin(event.sender_id):
                return
            
            admins = self.data['admins']
            self.data = self.load_data()
            self.data['admins'] = admins
            self.save_data()
            
            await event.reply("♻️ Semua pengaturan telah direset!")
        
        @self.client.on(events.NewMessage(pattern=r'^\.fitur$'))
        async def features_handler(event):
            if not await self.is_admin(event.sender_id):
                return
            
            features = """
📚 **DAFTAR FITUR USERBOT**

**📌 Tutorial & Info:**
• `.jasebking` - Tutorial penggunaan
• `.fitur` - Daftar semua fitur
• `.status` - Status userbot
• `.testformat` - Test emoji & formatting

**📁 Manajemen Grup:**
• `.cekgrub` - Cek semua grup
• `.setgrub 2 5 8` - Pilih grup tertentu
• `.setgrub all` - Pilih semua grup
• `.join @grup1 @grup2` - Join grup (max 5)
• `.out` - Keluar dari semua grup

**💬 Pengaturan Pesan:**
• `.pesan fw` - Set pesan forward (reply)
• `.pesan nofw` - Set pesan no forward (reply)
📸 Support: All media types + caption

**🤖 Kontrol Bot:**
• `.on` - Aktifkan bot
• `.off` - Nonaktifkan bot
• `.run 5` - Kirim tiap 5 menit
• `.run off` - Matikan timer

**💤 Mode Tidur:**
• `.tidur on` - Aktifkan mode tidur
• `.tidur off` - Nonaktifkan mode tidur
• `.tidur 22:00-06:00` - Set waktu tidur

**📨 Auto Reply PM:**
• `.pm on` - Aktifkan auto reply
• `.pm off` - Nonaktifkan auto reply
• `.pm <pesan>` - Set pesan auto reply

**⏱ Timer:**
• `.timer spam 5` - Delay antar spam (detik)
• `.timer grub 2` - Delay antar grup (detik)

**📬 Notifikasi:**
• `.notif @username` - Kirim notif ke user
• `.notif off` - Matikan notifikasi

**👥 Admin:**
• `.admin add @user` - Tambah admin
• `.admin del @user` - Hapus admin
• `.sudo <user_id>` - Tambah sudo
• `.delsudo <user_id>` - Hapus sudo
• `.listsudo` - Daftar sudo

**🔧 Lainnya:**
• `.reset all` - Reset semua pengaturan
"""
            await event.reply(features)
        
        @self.client.on(events.NewMessage(pattern=r'^\.status$'))
        async def status_handler(event):
            if not await self.is_admin(event.sender_id):
                return
            
            me = await self.client.get_me()
            
            msg_info = "Tidak ada"
            if self.data.get('message', {}).get('message_id'):
                msg_type = self.data['message'].get('media_type', 'Text')
                msg_mode = 'Forward' if self.data['message'].get('forward') else 'No Forward'
                msg_info = f"{msg_type} ({msg_mode})"
            
            status = f"""
📊 **STATUS USERBOT**

👤 **User:** {me.first_name}
🆔 **ID:** `{me.id}`
📱 **Username:** @{me.username or 'None'}

**⚙️ Pengaturan:**
• Bot Status: {'✅ Aktif' if self.data['bot_active'] else '❌ Nonaktif'}
• Grup Terpilih: {len(self.data.get('selected_groups', []))} grup
• Pesan Tersimpan: {msg_info}
• Timer: {self.data.get('run_timer', 'Off')} {'menit' if self.data.get('run_timer') else ''}
• Mode Tidur: {'✅ Aktif' if self.data.get('sleep_enabled', False) else '❌ Nonaktif'}
• Auto Reply PM: {'✅ Aktif' if self.data.get('pm_enabled', False) else '❌ Nonaktif'}
• Admin: {len(self.data.get('admins', []))} orang

**⏰ Timer Settings:**
• Spam Timer: {self.data.get('spam_timer', 5)} detik
• Group Timer: {self.data.get('group_timer', 1)} detik

**📸 Media Support:**
✅ Photo, Video, Document, Voice, Audio
✅ Sticker, GIF, dengan/tanpa caption
✅ Emoji premium & text formatting
"""
            await event.reply(status)
        
        @self.client.on(events.NewMessage(pattern=r'^\.sudo\s+(\d+)$'))
        async def add_sudo_handler(event):
            if event.sender_id != self.data['admins'][0]:
                return
            
            user_id = int(event.pattern_match.group(1))
            if user_id not in self.data['admins']:
                self.data['admins'].append(user_id)
                self.save_data()
                await event.reply(f"✅ User {user_id} ditambahkan sebagai sudo!")
            else:
                await event.reply("⚠️ User sudah menjadi sudo!")
        
        @self.client.on(events.NewMessage(pattern=r'^\.delsudo\s+(\d+)$'))
        async def del_sudo_handler(event):
            if event.sender_id != self.data['admins'][0]:
                return
            
            user_id = int(event.pattern_match.group(1))
            if user_id in self.data['admins'] and user_id != self.data['admins'][0]:
                self.data['admins'].remove(user_id)
                self.save_data()
                await event.reply(f"✅ User {user_id} dihapus dari sudo!")
            else:
                await event.reply("⚠️ Tidak dapat menghapus user ini!")
        
        @self.client.on(events.NewMessage(pattern=r'^\.listsudo$'))
        async def list_sudo_handler(event):
            if not await self.is_admin(event.sender_id):
                return
            
            sudo_list = "👥 **DAFTAR SUDO/ADMIN:**\n\n"
            for i, admin_id in enumerate(self.data['admins']):
                try:
                    user = await self.client.get_entity(admin_id)
                    sudo_list += f"{i+1}. {user.first_name} (`{admin_id}`)\n"
                except:
                    sudo_list += f"{i+1}. Unknown (`{admin_id}`)\n"
            
            await event.reply(sudo_list)
        
        @self.client.on(events.NewMessage(pattern=r'^\.testformat$'))
        async def test_format_handler(event):
            if not await self.is_admin(event.sender_id):
                return
            
            test_message = """
🎨 **TEST FORMATTING & EMOJI**

**Bold Text** | *Italic Text* | ***Bold Italic***
`Monospace Code` | ~~Strikethrough~~ | __Underline__
||Spoiler Text|| | [Link Text](https://telegram.org)

**Emoji Test:**
😀 😃 😄 😁 😆 😅 😂 🤣 ☺️ 😊 
🔥 ⚡ ✨ 💫 💥 💢 💯 🎯 🎪 🎨

**Unicode:**
♠️ ♥️ ♦️ ♣️ ⚜️ 🔱 ⚡ ☄️ 🌟 ⭐

**Combined:**
***`Bold Italic Mono`*** | __*Underline Italic*__
~~**Strikethrough Bold**~~ | ||***Spoiler Bold Italic***||

✅ Jika semua format terlihat dengan benar, maka mode **NOFW** akan copy sempurna!

📸 **Media Support:**
• Photo + Caption ✅
• Video + Caption ✅
• Document ✅
• Voice Note ✅
• Audio File ✅
• Sticker ✅
• GIF ✅
"""
            await event.reply(test_message)
        
        # Auto reply PM handler
        @self.client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
        async def pm_auto_reply(event):
            if self.data.get('pm_enabled', False) and self.data.get('pm_message'):
                if event.sender_id not in self.data['admins']:
                    await event.reply(self.data['pm_message'])
    
    async def is_admin(self, user_id):
        """Check if user is admin"""
        return user_id in self.data['admins']
    
    async def is_sleep_time(self):
        """Check if current time is in sleep period"""
        if not self.data.get('sleep_enabled', False):
            return False
        
        now = datetime.now().time()
        start_time = datetime.strptime(self.data['sleep_time']['start'], '%H:%M').time()
        end_time = datetime.strptime(self.data['sleep_time']['end'], '%H:%M').time()
        
        if start_time <= end_time:
            return start_time <= now <= end_time
        else:
            return now >= start_time or now <= end_time
    
    async def send_admin_notif(self, message):
        """Send notification to admin"""
        try:
            for admin_id in self.data['admins']:
                await self.client.send_message(admin_id, message)
        except:
            pass
    
    async def send_message_to_group(self, group_id, message_data):
        """Send message to a group with perfect copy including all media and formatting"""
        try:
            if message_data.get('forward'):
                # Forward the original message
                return await self.client.forward_messages(
                    group_id,
                    message_data['message_id'],
                    message_data['from_id']
                )
            else:
                # Get the original message for perfect copy
                original_msg = await self.client.get_messages(
                    message_data.get('chat_id', message_data['from_id']),
                    ids=message_data['message_id']
                )
                
                if not original_msg:
                    raise Exception("Original message not found")
                
                # Send with exact same formatting and media
                # This handles ALL media types
                return await self.client.send_message(
                    group_id,
                    message=original_msg.message,
                    file=original_msg.media,
                    formatting_entities=original_msg.entities,
                    buttons=original_msg.buttons,
                    link_preview=original_msg.web_preview
                )
                
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            raise e
    
    async def timer_loop(self):
        """Main timer loop for sending messages"""
        while self.running and self.data.get('run_timer'):
            try:
                if await self.is_sleep_time():
                    await asyncio.sleep(60)
                    continue
                
                if not self.data.get('bot_active', True):
                    await asyncio.sleep(60)
                    continue
                
                if not self.data.get('message', {}).get('message_id'):
                    logger.warning("No message set for broadcasting")
                    await asyncio.sleep(60)
                    continue
                
                # Send messages to selected groups
                success = 0
                failed = 0
                start_time = datetime.now()
                
                for group in self.data.get('selected_groups', []):
                    try:
                        await self.send_message_to_group(group['id'], self.data['message'])
                        success += 1
                        await asyncio.sleep(self.data.get('group_timer', 1))
                    except FloodWaitError as e:
                        logger.warning(f"Flood wait: {e.seconds} seconds")
                        await asyncio.sleep(e.seconds)
                    except Exception as e:
                        failed += 1
                        logger.error(f"Failed to send to {group['title']}: {e}")
                
                time_taken = (datetime.now() - start_time).seconds
                
                # Send notification if enabled
                if self.data.get('notif_user'):
                    try:
                        media_info = ""
                        if self.data['message'].get('media_type'):
                            media_info = f"📎 Media: {self.data['message']['media_type']}\n"
                        
                        await self.client.send_message(
                            self.data['notif_user'],
                            f"📊 **LAPORAN PENGIRIMAN**\n\n"
                            f"✅ Berhasil: {success}/{len(self.data.get('selected_groups', []))}\n"
                            f"❌ Gagal: {failed}\n"
                            f"{media_info}"
                            f"⏱ Waktu: {time_taken} detik\n"
                            f"⏰ Selesai: {datetime.now().strftime('%H:%M:%S')}"
                        )
                    except:
                        pass
                
                logger.info(f"Broadcast complete: {success} success, {failed} failed")
                
                # Wait for next cycle
                await asyncio.sleep(self.data['run_timer'] * 60)
                
            except Exception as e:
                logger.error(f"Timer loop error: {e}")
                await asyncio.sleep(60)

# ==================== MAIN FUNCTION ====================
async def main():
    """Main function"""
    bot = UserBot()
    await bot.start()

# ==================== RUN SCRIPT ====================
if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 TELEGRAM USERBOT JASEBKING")
    print("📌 Version: 2.0 FULL FEATURED")
    print("📸 Support: All Media + Emoji Premium")
    print("="*50 + "\n")
    
    # Check API credentials
    if API_ID == 12345678 or API_HASH == 'abcdef1234567890abcdef1234567890':
        print("❌ ERROR: API credentials belum diganti!")
        print("\n📝 Cara mendapatkan API credentials:")
        print("1. Buka https://my.telegram.org")
        print("2. Login dengan nomor telepon")
        print("3. Klik 'API Development Tools'")
        print("4. Create New Application")
        print("5. Copy API_ID dan API_HASH")
        print("6. Ganti di line 24-25 file ini")
        print("\n" + "="*50)
        exit(1)
    
    # Run bot
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Bot dihentikan oleh user!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 Kemungkinan solusi:")
        print("1. Cek koneksi internet")
        print("2. Pastikan API_ID dan API_HASH benar")
        print("3. Hapus file userbot.session dan coba lagi")
        print("4. Install telethon: pip install telethon")

# ==================== END OF SCRIPT ====================
