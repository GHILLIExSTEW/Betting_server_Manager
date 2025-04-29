from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
import os
import aiosqlite
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from io import BytesIO
import requests

class StatsImageGenerator:
    def __init__(self):
        self.image_width = 1200
        self.image_height = 800
        self.background_color = (20, 20, 30)  # Dark background
        self.text_color = (255, 255, 255)  # White text
        self.accent_color = (0, 150, 255)  # Blue accent
        self.font_path = "bot/assets/fonts/Roboto-Regular.ttf"
        self.font_bold_path = "bot/assets/fonts/Roboto-Bold.ttf"
        
    async def generate_stats_image(self, stats_data: dict, is_server: bool, guild_id: int, 
                                 user_id: int = None, guild_image_mask: str = None) -> str:
        """Generate a stats image with the specified data."""
        # Create base image
        image = Image.new('RGB', (self.image_width, self.image_height), self.background_color)
        draw = ImageDraw.Draw(image)
        
        # Load fonts
        title_font = ImageFont.truetype(self.font_bold_path, 48)
        subtitle_font = ImageFont.truetype(self.font_bold_path, 36)
        stat_font = ImageFont.truetype(self.font_bold_path, 32)
        label_font = ImageFont.truetype(self.font_path, 24)
        
        # Add guild image mask if available (for paid tiers)
        if guild_image_mask:
            try:
                response = requests.get(guild_image_mask)
                guild_img = Image.open(BytesIO(response.content))
                guild_img = guild_img.resize((100, 100))
                image.paste(guild_img, (20, 20), guild_img)
            except Exception as e:
                print(f"Error loading guild image: {e}")
        
        # Get capper's logo if not server stats
        if not is_server:
            async with aiosqlite.connect('bot/data/betting.db') as db:
                async with db.execute(
                    "SELECT image_path FROM cappers WHERE user_id = ? AND guild_id = ?",
                    (user_id, guild_id)
                ) as cursor:
                    result = await cursor.fetchone()
                    if result and result[0]:
                        try:
                            capper_logo = Image.open(result[0])
                            # Add shadow effect
                            shadow = Image.new('RGBA', capper_logo.size, (0, 0, 0, 128))
                            shadow = shadow.filter(ImageFilter.GaussianBlur(radius=10))
                            image.paste(shadow, (self.image_width//2 - capper_logo.width//2 + 5, 
                                               self.image_height//2 - capper_logo.height//2 + 5), 
                                      shadow)
                            image.paste(capper_logo, (self.image_width//2 - capper_logo.width//2, 
                                                    self.image_height//2 - capper_logo.height//2), 
                                      capper_logo)
                        except Exception as e:
                            print(f"Error loading capper logo: {e}")
        
        # Add title
        title = "Server Statistics" if is_server else "Capper Statistics"
        draw.text((self.image_width//2, 50), title, self.text_color, font=title_font, anchor="mm")
        
        # Add stats
        stats_y = 150
        stats_spacing = 60
        
        # W/L Ratio
        wl_ratio = f"{stats_data['wins']}/{stats_data['losses']}"
        draw.text((100, stats_y), "W/L Ratio:", self.text_color, font=label_font)
        draw.text((300, stats_y), wl_ratio, self.accent_color, font=stat_font)
        
        # Highest Odds Bet Won
        if 'highest_odds' in stats_data:
            draw.text((100, stats_y + stats_spacing), "Highest Odds Won:", self.text_color, font=label_font)
            draw.text((300, stats_y + stats_spacing), f"+{stats_data['highest_odds']}", 
                     self.accent_color, font=stat_font)
        
        # Favorite League
        if 'favorite_league' in stats_data:
            draw.text((100, stats_y + stats_spacing*2), "Favorite League:", self.text_color, font=label_font)
            draw.text((300, stats_y + stats_spacing*2), stats_data['favorite_league'], 
                     self.accent_color, font=stat_font)
        
        # Favorite Team
        if 'favorite_team' in stats_data:
            draw.text((100, stats_y + stats_spacing*3), "Favorite Team:", self.text_color, font=label_font)
            draw.text((300, stats_y + stats_spacing*3), stats_data['favorite_team'], 
                     self.accent_color, font=stat_font)
        
        # Favorite Player
        if 'favorite_player' in stats_data:
            draw.text((100, stats_y + stats_spacing*4), "Favorite Player:", self.text_color, font=label_font)
            draw.text((300, stats_y + stats_spacing*4), stats_data['favorite_player'], 
                     self.accent_color, font=stat_font)
        
        # Generate trend line
        if 'recent_performance' in stats_data:
            plt.figure(figsize=(8, 4))
            dates = [datetime.now() - timedelta(days=i) for i in range(len(stats_data['recent_performance']))]
            values = stats_data['recent_performance']
            
            # Plot actual data
            plt.plot(dates, values, 'o-', color='#0096FF', linewidth=2)
            
            # Add trend line
            x = np.arange(len(values))
            z = np.polyfit(x, values, 1)
            p = np.poly1d(z)
            plt.plot(dates, p(x), '--', color='#FF6B6B', linewidth=2)
            
            # Project next 7 days
            future_dates = [dates[-1] + timedelta(days=i) for i in range(1, 8)]
            future_values = p(np.arange(len(values), len(values) + 7))
            plt.plot(future_dates, future_values, ':', color='#4CAF50', linewidth=2)
            
            plt.title('Performance Trend', color='white')
            plt.grid(True, alpha=0.3)
            plt.gca().set_facecolor('#14141F')
            plt.gcf().set_facecolor('#14141F')
            plt.gca().tick_params(colors='white')
            
            # Save trend plot to BytesIO
            trend_buffer = BytesIO()
            plt.savefig(trend_buffer, format='png', facecolor='#14141F', edgecolor='none')
            plt.close()
            
            # Paste trend plot onto main image
            trend_img = Image.open(trend_buffer)
            image.paste(trend_img, (600, 150))
        
        # Save the image
        output_path = f"bot/assets/temp/stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        image.save(output_path)
        
        return output_path 