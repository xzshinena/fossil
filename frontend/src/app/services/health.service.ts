import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface TreeNode {
  id: number;
  name: string;
  health_score: number | null;
  partial: boolean;
  source_breakdown: Record<string, number>;
  children: TreeNode[];
}

@Injectable({ providedIn: 'root' })
export class HealthService {
  constructor(private http: HttpClient) {}

  getTree(year: number, month: number): Observable<TreeNode> {
    return this.http.get<TreeNode>(`${environment.apiUrl}/tree/`, {
      params: { year: year.toString(), month: month.toString() },
    });
  }
}
