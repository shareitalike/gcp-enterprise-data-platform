import uuid
import pandas as pd
from datetime import timedelta, datetime, timezone
from typing import Any

from .base import BaseGenerator


class CampaignGenerator(BaseGenerator):
    @property
    def entity_name(self) -> str:
        return "campaigns"

    @property
    def schema_version(self) -> str:
        return "1.0"

    def generate(self, count: int, **kwargs: Any) -> pd.DataFrame:
        records = []
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        
        types = ["EMAIL", "SMS", "PAID_SEARCH", "DISPLAY", "SOCIAL"]
        channels = ["Google", "Facebook", "Instagram", "Internal CRM"]
        
        for i in range(count):
            start_date = self.faker.date_between(start_date="-1y", end_date="+1m")
            # end date between 1 and 60 days after start
            end_date = start_date + timedelta(days=self.faker.random_int(min=1, max=60))
            
            budget = round(self.faker.random.uniform(100.0, 50000.0), 2)
            spent = round(budget * self.faker.random.uniform(0.1, 1.0), 2)
            
            records.append({
                "campaign_id": str(uuid.UUID(int=self.faker.random.getrandbits(128), version=4)),
                "source_campaign_id": f"CAMP-{1000 + i}",
                "campaign_name": f"{self.faker.word().capitalize()} Promo {start_date.year}",
                "campaign_type": self.faker.random_element(elements=types),
                "channel": self.faker.random_element(elements=channels),
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "budget_amount": budget,
                "spent_amount": spent,
                "target_segment": self.faker.random_element(elements=("BRONZE", "SILVER", "GOLD", "PLATINUM", "ALL", None)),
                "is_active": self.faker.boolean(chance_of_getting_true=30),
                "created_at": now,
                "updated_at": now,
                "_schema_version": self.schema_version,
            })
            
        df = pd.DataFrame(records)
        self.validate_dataframe(df)
        return df
