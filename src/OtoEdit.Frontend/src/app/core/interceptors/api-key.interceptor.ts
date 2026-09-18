import { HttpInterceptorFn } from '@angular/common/http';
import { environment } from '../../../environments/environment';

export const apiKeyInterceptor: HttpInterceptorFn = (req, next) => {
  const apiKey = environment.apiKey || 'SUPER_SECRET_OTOEDIT_KEY_123!';
  const authReq = req.clone({
    headers: req.headers.set('X-API-Key', apiKey)
  });
  return next(authReq);
};
