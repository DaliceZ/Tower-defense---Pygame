import pygame
import os
from utils.load_audio import play_button_sfx

class Button:
    def __init__(self, rect, text, font,
                 bg_color=(70, 70, 70),
                 hover_color=(120, 120, 120),
                 text_color=(51,25,0),
                 image_path=None,
                 subtext=None,
                 subfont=None):

        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font
        self.subtext = subtext
        self.subfont = subfont
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.text_color = text_color
        
        self.image = None
        self.hover_image = None
        if image_path and os.path.exists(image_path):
            img = pygame.image.load(image_path).convert_alpha()
            self.image = pygame.transform.scale(img, (self.rect.width, self.rect.height))
            self.hover_image = pygame.transform.scale(img, (self.rect.width + 10, self.rect.height + 4))

    def draw(self, screen):
        mouse_pos = pygame.mouse.get_pos()
        is_hovered = self.rect.collidepoint(mouse_pos)
        
        if self.image:
            if is_hovered:
                # Center the slightly larger hover image
                hover_rect = self.hover_image.get_rect(center=self.rect.center)
                screen.blit(self.hover_image, hover_rect)
            else:
                screen.blit(self.image, self.rect)
        else:
            color = self.hover_color if is_hovered else self.bg_color
            
            # Shadow
            shadow_surface = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
            pygame.draw.rect(shadow_surface, (0, 0, 0, 50), shadow_surface.get_rect(), border_radius=15)
            screen.blit(shadow_surface, (self.rect.x + 4, self.rect.y + 6))
            
            draw_rect = self.rect.copy()
            if is_hovered:
                draw_rect.inflate_ip(10, 0)
                
            pygame.draw.rect(screen, color, draw_rect, border_radius=15)
            pygame.draw.rect(screen, (255, 255, 255, 30), draw_rect, 2, border_radius=15)

        # Draw main text
        y_offset = -2 if not self.subtext else -8
        text_surf = self.font.render(self.text, True, self.text_color)
        text_rect = text_surf.get_rect(center=(self.rect.centerx, self.rect.centery + y_offset))
        screen.blit(text_surf, text_rect)
        
        # Draw subtext
        if self.subtext and self.subfont:
            sub_surf = self.subfont.render(self.subtext, True, (255,255,255) if self.image else (150, 150, 160))
            sub_rect = sub_surf.get_rect(center=(self.rect.centerx, self.rect.centery + 16 if self.image else self.rect.bottom + 15))
            screen.blit(sub_surf, sub_rect)

    def clicked(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                play_button_sfx()
                return True
        return False