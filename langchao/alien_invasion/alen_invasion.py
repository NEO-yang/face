import sys
import pygame 
from settings import Settings
from ship import Ship
import game_functions as gf

def run_game():
    pygame.init()
    # screen = pygame.display.set_mode((1200,800))

    ai_settings = Settings()
    screen = pygame.display.set_mode(
        (ai_settings.screen_width,ai_settings.screen_height)
    )

    pygame.display.set_caption("Alien Invasion")
    ship = Ship(ai_settings,screen)

    # bg_color =(230,230,230)

    while True:
        gf.check_events(ship)
        ship.update()
        gf.update_screen(ai_settings,screen,ship)

run_game()


