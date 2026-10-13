import os
import sys
import json
import csv
import base64
from getpass import getpass
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.align import Align
from rich import print as rprint

console = Console()

# FIX: When compiled with PyInstaller, __file__ points to a temporary extraction folder.
# sys.executable ensures the vault saves to the actual USB directory, not a temp folder.
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

VAULT_FILE = os.path.join(APP_DIR, "vault.ppm")
VERSION = "0.0.1 (development)"

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def draw_header():
    ascii_ppm = """[bold cyan]
██████╗ ██████╗ ███╗   ███╗
██╔══██╗██╔══██╗████╗ ████║
██████╔╝██████╔╝██╔████╔██║
██╔═══╝ ██╔═══╝ ██║╚██╔╝██║
██║     ██║     ██║ ╚═╝ ██║
╚═╝     ╚═╝     ╚═╝     ╚═╝[/bold cyan]"""

    subtitle = f"[dim]Portable Password Manager[/dim]\n[bold magenta]Version: {VERSION}[/bold magenta]"
    content = f"{ascii_ppm}\n\n{subtitle}"
    rprint(Panel(Align.center(content), border_style="cyan", padding=(1, 2)))

def show_credits():
    clear_screen()
    draw_header()
    credits_text = (
        "\n[bold green]Lead Developer:[/bold green] Pratyush\n\n"
        "[bold cyan]Powered By:[/bold cyan] Python, Cryptography (AES-128), and Rich\n\n"
        "[dim]Built for absolute USB portability. The vault file stays\n"
        "strictly in the executable's directory, leaving zero trace on the host machine.[/dim]\n"
    )
    rprint(Panel(Align.center(credits_text), title="[bold]Credits & Info[/bold]", border_style="magenta", padding=(1, 2)))
    input("\nPress Enter to return...")

def get_key(master_password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,
    )
    return base64.urlsafe_b64encode(kdf.derive(master_password.encode()))

def load_vault(master_password: str):
    if not os.path.exists(VAULT_FILE):
        return {}
    
    with open(VAULT_FILE, 'rb') as f:
        data = f.read()
    
    salt, encrypted_data = data[:16], data[16:]
    fernet = Fernet(get_key(master_password, salt))
    
    try:
        decrypted_data = fernet.decrypt(encrypted_data)
        return json.loads(decrypted_data.decode())
    except Exception:
        return None

def save_vault(master_password: str, data: dict):
    salt = os.urandom(16)
    fernet = Fernet(get_key(master_password, salt))
    encrypted_data = fernet.encrypt(json.dumps(data).encode())
    
    with open(VAULT_FILE, 'wb') as f:
        f.write(salt + encrypted_data)

def import_csv(vault: dict, filepath: str):
    try:
        with open(filepath, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                name = row.get('name', row.get('url', 'Unknown'))
                username = row.get('username', '')
                password = row.get('password', '')
                if password:
                    vault[name] = {"username": username, "password": password}
                    count += 1
            return count
    except Exception:
        return -1

def main():
    clear_screen()
    draw_header()
    master_password = getpass("🔑 Enter Master Password: ")
    
    vault = load_vault(master_password)
    
    if vault is None:
        rprint("[bold red]Access Denied. Incorrect Password or Corrupted Vault.[/bold red]")
        sys.exit(1)
        
    while True:
        clear_screen()
        draw_header()
        rprint("[1] 🔍 Search Passwords")
        rprint("[2] ➕ Add New Password")
        rprint("[3] 📥 Import from Edge/Chrome CSV")
        rprint("[4] ⚠️  Reset Master Password (WIPES VAULT)")
        rprint("[5] ❌ Delete Vault Entirely")
        rprint("[6] ℹ️  Credits & Info")
        rprint("[7] 🚪 Lock & Exit\n")
        
        choice = input("Select an option: ")
        
        if choice == '1':
            query = input("\nSearch (leave blank to list all): ").lower()
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Service/URL")
            table.add_column("Username")
            table.add_column("Password")
            
            for service, creds in vault.items():
                if query in service.lower() or query in creds['username'].lower():
                    table.add_row(service, creds['username'], creds['password'])
            
            console.print(table)
            input("\nPress Enter to return...")
            
        elif choice == '2':
            service = input("Service/URL: ")
            username = input("Username: ")
            password = getpass("Password: ")
            vault[service] = {"username": username, "password": password}
            save_vault(master_password, vault)
            rprint("[green]Saved securely![/green]")
            input("Press Enter to return...")
            
        elif choice == '3':
            filepath = input("Enter path to CSV file: ")
            count = import_csv(vault, filepath)
            if count >= 0:
                save_vault(master_password, vault)
                rprint(f"[green]Successfully imported {count} passwords![/green]")
            else:
                rprint("[red]Failed to read CSV. Ensure it is a valid browser export.[/red]")
            input("Press Enter to return...")
            
        elif choice == '4':
            rprint("\n[bold red]WARNING: This will DESTROY all saved passwords and reset your master password.[/bold red]")
            confirm = input("Type 'WIPE' to confirm: ")
            if confirm == 'WIPE':
                new_master = getpass("\nEnter NEW Master Password: ")
                new_master_confirm = getpass("Confirm NEW Master Password: ")
                if new_master == new_master_confirm:
                    master_password = new_master
                    vault = {}
                    save_vault(master_password, vault)
                    rprint("[bold green]Vault wiped and master password reset successfully![/bold green]")
                else:
                    rprint("[bold red]Passwords do not match. Aborted.[/bold red]")
            else:
                rprint("[yellow]Vault reset aborted.[/yellow]")
            input("\nPress Enter to return...")

        elif choice == '5':
            rprint("\n[bold red]WARNING: This will permanently delete 'vault.ppm' from your storage.[/bold red]")
            confirm = input("Type 'DELETE' to confirm: ")
            if confirm == 'DELETE':
                if os.path.exists(VAULT_FILE):
                    os.remove(VAULT_FILE)
                    rprint("[bold green]Vault deleted successfully. Exiting PPM.[/bold green]")
                    sys.exit(0)
                else:
                    rprint("[yellow]No vault file found to delete.[/yellow]")
            else:
                rprint("[yellow]Deletion aborted.[/yellow]")
            input("\nPress Enter to return...")

        elif choice == '6':
            show_credits()

        elif choice == '7':
            clear_screen()
            rprint("[bold green]Vault Locked. Goodbye![/bold green]")
            break

if __name__ == "__main__":
    main()