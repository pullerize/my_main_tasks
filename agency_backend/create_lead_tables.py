from app.database import engine
from app.models import Lead, LeadNote, LeadAttachment, LeadHistory

# Создаем только таблицы для лидов
Lead.__table__.create(engine, checkfirst=True)
LeadNote.__table__.create(engine, checkfirst=True) 
LeadAttachment.__table__.create(engine, checkfirst=True)
LeadHistory.__table__.create(engine, checkfirst=True)

print("Lead tables created successfully!")