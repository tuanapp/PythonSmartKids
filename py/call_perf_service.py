import os
import traceback
os.environ['ENVIRONMENT'] = 'production'

try:
    from app.services.performance_report_service import performance_report_service
    UID = 'zTCNkGbtvPRscMo98innxe1gqI73'
    print('Calling performance_report_service.get_performance_reports for', UID)
    reports = performance_report_service.get_performance_reports(UID)
    print('Returned count:', len(reports))
    if reports:
        print('First report id:', reports[0].get('id'))
        print('Success:', reports[0].get('success'))
    else:
        print('No reports returned')
except Exception as e:
    print('Exception during import or call:')
    traceback.print_exc()
