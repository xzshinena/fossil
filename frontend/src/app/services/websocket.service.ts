import { Injectable, NgZone } from '@angular/core';
import { Subject } from 'rxjs';
import { environment } from '../../environments/environment';

export interface ScoreUpdate {
  language_id: number;
  language: string;
  sub_score_type: string;
  delta: number;
  new_score: number;
  timestamp: string;
}

@Injectable({ providedIn: 'root' })
export class WebSocketService {
  updates$ = new Subject<ScoreUpdate>();
  connectionStatus$ = new Subject<'connected' | 'reconnecting' | 'disconnected'>();

  private ws: WebSocket | null = null;
  private retryDelay = 1000;
  private retryTimer: ReturnType<typeof setTimeout> | null = null;

  constructor(private zone: NgZone) {}

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) return;
    this._open();
  }

  disconnect(): void {
    if (this.retryTimer) clearTimeout(this.retryTimer);
    this.ws?.close();
    this.ws = null;
  }

  private _open(): void {
    this.ws = new WebSocket(`${environment.wsUrl}/ws/scores/`);

    this.ws.onopen = () => {
      this.retryDelay = 1000;
      this.zone.run(() => this.connectionStatus$.next('connected'));
    };

    this.ws.onmessage = (event) => {
      const data: ScoreUpdate = JSON.parse(event.data);
      this.zone.run(() => this.updates$.next(data));
    };

    this.ws.onclose = () => {
      this.zone.run(() => this.connectionStatus$.next('reconnecting'));
      this._scheduleReconnect();
    };

    this.ws.onerror = () => {
      this.ws?.close();
    };
  }

  private _scheduleReconnect(): void {
    this.retryTimer = setTimeout(() => {
      this._open();
      this.retryDelay = Math.min(this.retryDelay * 2, 30000);
    }, this.retryDelay);
  }
}
