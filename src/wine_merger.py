"""
Wine Merger Utility

This module provides functionality to merge wine information from one or two wines
into a combined format suitable for email generation.
"""

from typing import List, Optional, Union
from dataclasses import dataclass


@dataclass
class MergedWineInfo:
    """Merged wine information for email generation"""
    names: str
    producers: str
    countries: str
    grape_varieties: str
    descriptions: Optional[str] = None
    wine_count: int = 1


def merge_wines(wines: List) -> MergedWineInfo:
    """
    Merge one or two wines into a combined wine information object.
    
    Args:
        wines: List or tuple of wine objects (1 or 2 wines)
        
    Returns:
        MergedWineInfo: Combined wine information
        
    Raises:
        ValueError: If wines list is empty or contains more than 2 wines
    """
    if not wines:
        raise ValueError("At least one wine must be provided")
    
    if len(wines) > 2:
        raise ValueError("Maximum of 2 wines can be merged")
    
    wine_count = len(wines)
    
    if wine_count == 1:
        # Single wine - direct mapping
        wine = wines[0]
        return MergedWineInfo(
            names=wine.name or "",
            producers=wine.producer or "",
            countries=wine.country or "",
            grape_varieties=wine.grape_variety or "",
            descriptions=wine.description if hasattr(wine, 'description') else None,
            wine_count=1
        )
    
    else:
        # Two wines - merge with appropriate formatting
        wine1, wine2 = wines[0], wines[1]
        
        # Merge names
        names = _merge_field([wine1.name, wine2.name], " & ")
        
        # Merge producers
        producers = _merge_field([wine1.producer, wine2.producer], " / ")
        
        # Merge countries
        countries = _merge_field([wine1.country, wine2.country], " & ")
        
        # Merge grape varieties
        grape_varieties = _merge_field([wine1.grape_variety, wine2.grape_variety], " + ")
        
        # Merge descriptions
        descriptions = None
        desc1 = getattr(wine1, 'description', None)
        desc2 = getattr(wine2, 'description', None)
        
        if desc1 and desc2:
            descriptions = f"【{wine1.name or 'Wine 1'}】{desc1}\n\n【{wine2.name or 'Wine 2'}】{desc2}"
        elif desc1:
            descriptions = f"【{wine1.name or 'Wine 1'}】{desc1}"
        elif desc2:
            descriptions = f"【{wine2.name or 'Wine 2'}】{desc2}"
        
        return MergedWineInfo(
            names=names,
            producers=producers,
            countries=countries,
            grape_varieties=grape_varieties,
            descriptions=descriptions,
            wine_count=2
        )


def _merge_field(values: List[Optional[str]], separator: str) -> str:
    """
    Merge field values with deduplication and formatting.
    
    Args:
        values: List of field values (may contain None)
        separator: Separator to use between values
        
    Returns:
        str: Merged field value
    """
    # Filter out None and empty values
    clean_values = [v.strip() for v in values if v and v.strip()]
    
    if not clean_values:
        return ""
    
    # Remove duplicates while preserving order
    unique_values = []
    seen = set()
    for value in clean_values:
        if value.lower() not in seen:
            unique_values.append(value)
            seen.add(value.lower())
    
    return separator.join(unique_values)


def format_wine_preview(merged_wine: MergedWineInfo) -> str:
    """
    Format merged wine information for display preview.
    
    Args:
        merged_wine: MergedWineInfo object
        
    Returns:
        str: Formatted preview string
    """
    if merged_wine.wine_count == 1:
        parts = []
        if merged_wine.producers:
            parts.append(f"Producer: {merged_wine.producers}")
        if merged_wine.countries:
            parts.append(f"Country: {merged_wine.countries}")
        if merged_wine.grape_varieties:
            parts.append(f"Grape: {merged_wine.grape_varieties}")
        
        return " • ".join(parts) if parts else "Single wine selected"
    
    else:
        parts = []
        if merged_wine.countries:
            parts.append(f"Countries: {merged_wine.countries}")
        if merged_wine.grape_varieties:
            parts.append(f"Grapes: {merged_wine.grape_varieties}")
        
        return " • ".join(parts) if parts else "Two wines selected"


def get_wine_summary(merged_wine: MergedWineInfo) -> str:
    """
    Get a brief summary of the wine selection for UI display.
    
    Args:
        merged_wine: MergedWineInfo object
        
    Returns:
        str: Brief summary string
    """
    if merged_wine.wine_count == 1:
        return f"🍷 {merged_wine.names}"
    else:
        return f"🍷🍷 {merged_wine.names}" 