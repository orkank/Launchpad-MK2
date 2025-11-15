"""Rich-based colorized help system."""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich.align import Align


def show_help():
    """Display colorized help screen with Rich formatting."""
    console = Console()

    # Header
    header = Text("🎹 Launchpad MK2 Spotify Controller", style="bold magenta")
    header_panel = Panel(
        Align.center(header),
        style="bright_blue",
        padding=(1, 2)
    )

    console.print(header_panel)
    console.print()

    # Create command tables
    playlist_table = Table(title="🎵 Playlist Commands", show_header=True, header_style="bold green")
    playlist_table.add_column("Command", style="cyan", width=8)
    playlist_table.add_column("Description", style="white")

    playlist_table.add_row("p", "📥 Fetch and save playlists from Spotify")
    playlist_table.add_row("l", "📋 List available playlists")
    playlist_table.add_row("v", "👀 [bold]Preview playlist ↔ animation mappings[/bold]")
    playlist_table.add_row("g", "🤖 Generate automatic playlist mappings")
    playlist_table.add_row("r", "🎲 Randomize animations for all playlists")

    animation_table = Table(title="✨ Animation Commands", show_header=True, header_style="bold yellow")
    animation_table.add_column("Command", style="cyan", width=8)
    animation_table.add_column("Description", style="white")

    animation_table.add_row("a", "🎨 List and start animations manually")
    animation_table.add_row("x", "⏹️ Stop current animation")

    spotify_table = Table(title="🎧 Spotify Commands", show_header=True, header_style="bold blue")
    spotify_table.add_column("Command", style="cyan", width=8)
    spotify_table.add_column("Description", style="white")

    spotify_table.add_row("s", "📱 Show and select Spotify devices")

    system_table = Table(title="⚙️ System Commands", show_header=True, header_style="bold red")
    system_table.add_column("Command", style="cyan", width=8)
    system_table.add_column("Description", style="white")

    system_table.add_row("h", "❓ Show this help screen")
    system_table.add_row("q", "🚪 Quit application")

    # Layout tables in columns
    tables_layout = Columns([playlist_table, animation_table], equal=True, expand=True)
    console.print(tables_layout)
    console.print()

    tables_layout2 = Columns([spotify_table, system_table], equal=True, expand=True)
    console.print(tables_layout2)
    console.print()

    # Hardware controls section
    hardware_panel = Panel(
        """🎹 [bold cyan]Hardware Controls (Launchpad MK2)[/bold cyan]

[yellow]Top Row (Control Buttons):[/yellow]
• [cyan]Button (0,8)[/cyan]: 🔊 Volume Up        • [cyan]Button (1,8)[/cyan]: 🔉 Volume Down
• [cyan]Button (2,8)[/cyan]: ⏮️ Previous Track   • [cyan]Button (3,8)[/cyan]: ⏭️ Next Track
• [cyan]Button (4,8)[/cyan]: 🎯 Animation Select  • [cyan]Button (5,8)[/cyan]: ⏯️ Play/Pause
• [cyan]Button (7,8)[/cyan]: 🎲 Random Playlist

[yellow]Main Grid (0,0 to 7,7):[/yellow]
• Press any button to play the mapped playlist
• Each button can trigger a specific playlist + animation combo

[yellow]Animation Selection Mode:[/yellow]
• Press [cyan]Session (4,8)[/cyan] to enter/exit animation selection
• Grid buttons will show available animations
• Press any grid button to select that animation""",
        title="🎮 Hardware Guide",
        style="bright_green",
        padding=(1, 2)
    )

    console.print(hardware_panel)
    console.print()

    # Web interface info
    web_panel = Panel(
        """🌐 [bold cyan]Web Interface[/bold cyan]

[yellow]API Endpoints:[/yellow]
• [link]http://localhost:5125/[/link] - Web control panel
• [link]http://localhost:5125/mappings[/link] - Playlist mappings (JSON)
• [link]http://localhost:5125/animation/<name>[/link] - Start animation
• [link]http://localhost:5125/devices[/link] - Spotify devices (JSON)

[yellow]Features:[/yellow]
• 📱 Simple control panel for basic operations
• 🎵 Current playlist display
• ⏯️ Play/pause controls
• 🎨 Animation selection dropdown""",
        title="🌐 Web Features",
        style="bright_magenta",
        padding=(1, 2)
    )

    console.print(web_panel)
    console.print()

    # Tips section
    tips_text = Text()
    tips_text.append("💡 ", style="yellow")
    tips_text.append("Pro Tips:", style="bold")
    tips_text.append("\n• Use 'v' to see which playlists are mapped to which animations")
    tips_text.append("\n• Generate mappings first with 'g' if you have no playlists set up")
    tips_text.append("\n• The hardware controls work even when the terminal is busy")
    tips_text.append("\n• Animations automatically sync with Spotify playback state")
    tips_text.append("\n• Check the web interface for a graphical control panel")

    tips_panel = Panel(
        tips_text,
        title="✨ Tips & Tricks",
        style="bright_yellow",
        padding=(1, 2)
    )

    console.print(tips_panel)


def show_quick_status(playlist_manager, animation_controller, spotify_manager):
    """Show quick status overview."""
    console = Console()

    # Current status
    current_animation = animation_controller.current_animation or "None"
    mapped_playlists = len(playlist_manager.mappings)

    # Spotify status
    spotify_status = "❌ Disconnected"
    current_track = "None"

    if spotify_manager and spotify_manager.spotify:
        try:
            current = spotify_manager.spotify.current_playback()
            if current and current['item']:
                spotify_status = "✅ Connected"
                track_name = current['item']['name'][:30]
                if len(current['item']['name']) > 30:
                    track_name += "..."
                current_track = track_name
            else:
                spotify_status = "⏸️ Not Playing"
        except:
            spotify_status = "⚠️ Error"

    status_table = Table(title="📊 Quick Status", show_header=True, header_style="bold cyan")
    status_table.add_column("Item", style="yellow", width=20)
    status_table.add_column("Status", style="white", width=40)

    status_table.add_row("🎨 Current Animation", current_animation)
    status_table.add_row("🎵 Mapped Playlists", str(mapped_playlists))
    status_table.add_row("🎧 Spotify", spotify_status)
    status_table.add_row("🎶 Current Track", current_track)

    console.print(status_table)
    console.print()

    # Show simple help after status
    show_simple_help()


def show_simple_help():
    """Show simplified command help for startup."""
    console = Console()

    # Simple commands list
    commands_text = """[bold cyan]Available Commands:[/bold cyan]
[yellow]h[/yellow] - Show detailed help        [yellow]v[/yellow] - Preview playlist mappings
[yellow]s[/yellow] - Spotify devices          [yellow]p[/yellow] - Fetch playlists
[yellow]a[/yellow] - Start animations         [yellow]x[/yellow] - Stop animation
[yellow]g[/yellow] - Generate mappings        [yellow]r[/yellow] - Randomize animations
[yellow]q[/yellow] - Quit                     [dim]Web: http://localhost:5125[/dim]
"""

    console.print(commands_text)
    console.print("💡 [dim]Type 'h' for detailed help with hardware controls and tips[/dim]")
    console.print()
