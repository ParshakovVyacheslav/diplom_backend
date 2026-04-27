# views.py
from django.http import HttpResponse
import requests
import logging

logger = logging.getLogger(__name__)

def activate_user(request, uid, token):
    try:
        scheme = 'https' if request.is_secure() else 'http'
        domain = request.get_host()
        
        djoser_url = f"http://127.0.0.1:8000/auth/users/activation/"
        
        response = requests.post(
            djoser_url,
            json={'uid': uid, 'token': token},
            timeout=5
        )
        
        if response.status_code == 204:
            return HttpResponse('''
                <h1>Аккаунт активирован!</h1>
                <p>Теперь вы можете войти в приложение.</p>
            ''')
        else:
            return HttpResponse('''
                <h1>Ошибка активации</h1>
                <p>Ссылка недействительна или устарела.</p>
                <p>Код ошибки: ''' + str(response.status_code) + '''</p>
            ''', status=400)
            
    except requests.exceptions.RequestException as e:
        return HttpResponse('''
            <h1>Ошибка соединения</h1>
            <p>Попробуйте позже или свяжитесь с поддержкой.</p>
        ''', status=500)