"""
UniversalQR - User Identity & Dynamic Avatar/Logo Generator
Generates high-resolution, vector-based personalized avatars and brand identity logos
matching the UniversalQR design system.
"""

import os
import hashlib

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
AVATAR_FOLDER = os.path.join(BASE_DIR, "static", "avatars")
os.makedirs(AVATAR_FOLDER, exist_ok=True)

# Curated modern gradient pairs
GRADIENT_PAIRS = [
    ("#4F46E5", "#06B6D4"),  # Indigo to Cyan
    ("#7C3AED", "#EC4899"),  # Purple to Pink
    ("#2563EB", "#38BDF8"),  # Blue to Light Sky
    ("#0D9488", "#10B981"),  # Teal to Emerald
    ("#D97706", "#F59E0B"),  # Amber to Gold
    ("#E11D48", "#FB7185"),  # Rose to Crimson
    ("#4338CA", "#6366F1"),  # Deep Indigo to Bright Indigo
    ("#059669", "#34D399"),  # Forest to Mint
]

def get_initials(name):
    if not name:
        return "UQ"
    parts = name.strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    elif len(parts) == 1 and len(parts[0]) >= 2:
        return parts[0][:2].upper()
    elif len(parts) == 1:
        return parts[0][0].upper()
    return "UQ"

def pick_gradient(seed_string):
    md5_hash = hashlib.md5(str(seed_string).encode("utf-8")).hexdigest()
    idx = int(md5_hash, 16) % len(GRADIENT_PAIRS)
    return GRADIENT_PAIRS[idx]

def generate_user_avatar_svg(user_id, name, user_code=""):
    """
    Generates a personalized SVG avatar and saves it to static/avatars/<user_id>.svg.
    Returns relative path 'avatars/<user_id>.svg'.
    """
    initials = get_initials(name)
    color1, color2 = pick_gradient(user_id or name)
    short_code = user_code if user_code else "UQR"

    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">
  <defs>
    <linearGradient id="grad-{user_id}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{color1}" />
      <stop offset="100%" stop-color="{color2}" />
    </linearGradient>
    <filter id="shadow" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="4" stdDeviation="6" flood-opacity="0.25"/>
    </filter>
  </defs>

  <!-- Background Circle with Gradient -->
  <circle cx="100" cy="100" r="92" fill="url(#grad-{user_id})" filter="url(#shadow)" />
  
  <!-- Subtle Outer Ring -->
  <circle cx="100" cy="100" r="88" fill="none" stroke="rgba(255, 255, 255, 0.35)" stroke-width="2.5" stroke-dasharray="6 4" />
  
  <!-- Tech Accent Pattern -->
  <circle cx="100" cy="100" r="70" fill="none" stroke="rgba(255, 255, 255, 0.15)" stroke-width="1.5" />

  <!-- Initials Text -->
  <text x="100" y="112" font-family="'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" 
        font-size="62" font-weight="800" fill="#ffffff" text-anchor="middle" dominant-baseline="middle" letter-spacing="-1">
    {initials}
  </text>

  <!-- Brand Seal Badge -->
  <g transform="translate(100, 162)">
    <rect x="-38" y="-11" width="76" height="19" rx="9.5" fill="rgba(15, 23, 42, 0.75)" stroke="rgba(255, 255, 255, 0.3)" stroke-width="1" />
    <text x="0" y="3.5" font-family="'Inter', sans-serif" font-size="9" font-weight="700" fill="#ffffff" text-anchor="middle" letter-spacing="1">
      {short_code}
    </text>
  </g>
</svg>'''

    filename = f"{user_id}.svg"
    full_path = os.path.join(AVATAR_FOLDER, filename)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(svg_content)

    return f"avatars/{filename}"
