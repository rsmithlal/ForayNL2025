from django.contrib import admin
from .models import (
    ForayFungi2023, MycoBankList,
    ForayMatch, ForayPerfectMatch, ForayMismatchExplanation,
    ForayPerfectMycoMatch, ForayMismatchMycoScores, ReviewedMatch
)

for m in [ForayFungi2023, MycoBankList, ForayMatch, ForayPerfectMatch,
          ForayMismatchExplanation, ForayPerfectMycoMatch, ForayMismatchMycoScores,
          ReviewedMatch]:
    try:
        admin.site.register(m)
    except admin.sites.AlreadyRegistered:
        pass
