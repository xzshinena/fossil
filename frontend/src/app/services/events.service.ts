import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface HistoricalEvent {
  id: number;
  date: string;           // YYYY-MM-DD
  title: string;
  language: number | null;
  language_name: string | null;
  impact_description: string;
}

@Injectable({ providedIn: 'root' })
export class EventsService {
  constructor(private http: HttpClient) {}

  getEvents(): Observable<{ results: HistoricalEvent[] }> {
    return this.http.get<{ results: HistoricalEvent[] }>(
      `${environment.apiUrl}/events/?page_size=100`
    );
  }
}
