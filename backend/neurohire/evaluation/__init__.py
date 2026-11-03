"""
NeuroHire evaluation (paper §IV.G). Run with:

    python manage.py evaluate --dataset evaluation_data/frontend_12 --similarity tfidf
    python manage.py evaluate --dataset evaluation_data/frontend_12 --similarity gemini   # needs GEMINI_API_KEY
    python manage.py annotation_sheet --dataset evaluation_data/frontend_12
    python manage.py agreement --csv annotations.csv
"""
