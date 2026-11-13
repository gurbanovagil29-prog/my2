import json,urllib.request,time,sys
def get(u):
    for i in range(5):
        try:
            r=urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'})
            return urllib.request.urlopen(r,timeout=40).read()
        except Exception as e:
            print('retry',u[:90],e,file=sys.stderr); time.sleep(2+i*2)
    raise SystemExit('fail '+u)
tick=sys.argv[2:]
for t in tick:
    u=f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?period1=1604188800&period2=1767312000&interval=1mo&events=div,split&includeAdjustedClose=true"
    open(f"{sys.argv[1]}/px_{t}.json",'wb').write(get(u)); time.sleep(0.5)
    if not t.startswith('^'):
        types=','.join(['quarterly'+x for x in ['TotalDebt','CapitalLeaseObligations','LongTermDebt','CurrentDebt','MarketCap','OrdinarySharesNumber','StockholdersEquity','TaxRateForCalcs','LongTermCapitalLeaseObligation','CurrentCapitalLeaseObligation','CurrentDebtAndCapitalLeaseObligation','LongTermDebtAndCapitalLeaseObligation']]+['annualTaxRateForCalcs','annualPretaxIncome','annualTaxProvision','annualTotalRevenue','annualEBIT','annualTotalDebt'])
        u=f"https://query1.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/{t}?type={types}&period1=1704067200&period2=1790000000"
        open(f"{sys.argv[1]}/fu_{t}.json",'wb').write(get(u)); time.sleep(0.5)
    print('ok',t)
