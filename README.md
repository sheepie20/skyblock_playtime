# Playtime Tracker Bot

## Overview
This Discord bot allows users to submit their playtime for specific dates and stores the data in an SQLite database. Users can generate graphs to visualize their playtime over time and compare their playtime with other users.

## Features
- **Submit Playtime**: Users can submit their playtime using the `/submit` command.
- **Graph Playtime**: Users can generate a line chart of their playtime history using `/graph`.
- **Compare Playtime**: Users can compare their playtime with another user's using `/compare`.
- **SQLite Storage**: Data is stored in an SQLite database for persistence.
- **Global Usage**: The bot can be installed on user accounts and used in both DMs and servers.

## Installation

### Requirements
- Python 3.8+
- `discord.py` library
- `matplotlib` for generating graphs
- SQLite (included with Python)

### Setup
1. Clone this repository:
   ```bash
   git clone https://github.com/sheepie20/skyblock_playtime.git
   cd skyblock_playtime
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up your bot token in `.env`:
   ```python
   token="your token here"
   ```
4. Run the bot:
   ```bash
   python main.py
   ```

## Commands

### `/submit <playtime> [date]`
- Submit playtime for a specific date.
- Example: `/submit 3.5 2025-03-20`

### `/graph`
- Generates a line chart of your total playtime over all recorded dates.
- Example: `/graph`

### `/compare <user1> <user2>`
- Generates a line chart comparing your playtime to another user's.
- Example: `/compare @user1 @user2`

## Contributing
Pull requests are welcome! If you have suggestions or want to report an issue, feel free to open an issue on GitHub.

## License
This project is licensed under the MIT License.

## Credits
Developed by sheepie20.

