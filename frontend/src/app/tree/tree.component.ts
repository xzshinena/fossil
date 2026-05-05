import {
  AfterViewInit, Component, ElementRef, OnDestroy, OnInit, ViewChild,
} from '@angular/core';
import { Subscription } from 'rxjs';
import * as d3 from 'd3';

import { HealthService, TreeNode } from '../services/health.service';
import { WebSocketService } from '../services/websocket.service';
import { EventsService, HistoricalEvent } from '../services/events.service';

const MIN_YEAR = 2011;
const MAX_YEAR = 2024;
const TOTAL_MONTHS = (MAX_YEAR - MIN_YEAR) * 12 + 12; // 168
const TRANSITION_DURATION = window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 150;

@Component({
  selector: 'app-tree',
  templateUrl: './tree.component.html',
  styleUrls: ['./tree.component.css'],
})
export class TreeComponent implements OnInit, AfterViewInit, OnDestroy {
  @ViewChild('treeContainer', { static: true }) containerRef!: ElementRef<HTMLDivElement>;

  sliderValue = TOTAL_MONTHS - 1;  // default to Dec 2024
  connectionStatus: 'connected' | 'reconnecting' | 'disconnected' | null = null;
  events: HistoricalEvent[] = [];
  activeTooltip: HistoricalEvent | null = null;
  treeEmpty = true;

  get displayDate(): string {
    const { year, month } = this._sliderToDate(this.sliderValue);
    return `${year} / ${month.toString().padStart(2, '0')}`;
  }

  private svg!: d3.Selection<SVGSVGElement, unknown, null, undefined>;
  private g!: d3.Selection<SVGGElement, unknown, null, undefined>;
  private width = 0;
  private height = 0;
  private margin = { top: 30, right: 180, bottom: 30, left: 80 };

  private colorScale = d3.scaleSequential(d3.interpolateRdYlGn).domain([0, 100]);

  private subs = new Subscription();

  constructor(
    private health: HealthService,
    private ws: WebSocketService,
    private eventsService: EventsService,
  ) {}

  /** Convert an event date string (YYYY-MM-DD) to a slider index (0–167). */
  eventSliderPos(event: HistoricalEvent): number {
    const [year, month] = event.date.split('-').map(Number);
    return (year - MIN_YEAR) * 12 + (month - 1);
  }

  /** Left % position of a pin on the slider track. */
  pinLeft(event: HistoricalEvent): string {
    return `${(this.eventSliderPos(event) / (TOTAL_MONTHS - 1)) * 100}%`;
  }

  showTooltip(event: HistoricalEvent): void { this.activeTooltip = event; }
  hideTooltip(): void { this.activeTooltip = null; }

  jumpToEvent(event: HistoricalEvent): void {
    this.sliderValue = this.eventSliderPos(event);
    this._loadTree();
  }

  ngOnInit(): void {
    this.ws.connect();
    this.subs.add(
      this.ws.connectionStatus$.subscribe(s => this.connectionStatus = s)
    );
    this.subs.add(
      this.ws.updates$.subscribe(update => {
        if (this.g) this._applyLiveUpdate(update);
      })
    );
  }

  ngAfterViewInit(): void {
    setTimeout(() => {
      this._initSvg();
      this._loadTree();
      this.eventsService.getEvents().subscribe({
        next: res => this.events = res,
        error: () => {},
      });
    }, 0);
  }

  ngOnDestroy(): void {
    this.ws.disconnect();
    this.subs.unsubscribe();
  }

  onSliderChange(): void {
    this._loadTree();
  }

  private _sliderToDate(index: number): { year: number; month: number } {
    return {
      year: MIN_YEAR + Math.floor(index / 12),
      month: (index % 12) + 1,
    };
  }

  private _initSvg(): void {
    const el = this.containerRef.nativeElement;
    this.width = el.clientWidth || 960;
    this.height = el.clientHeight || 620;

    this.svg = d3.select(el)
      .append('svg')
      .attr('width', this.width)
      .attr('height', this.height);

    this.g = this.svg
      .append('g')
      .attr('transform', `translate(${this.margin.left},${this.margin.top})`);
  }

  private _loadTree(): void {
    const { year, month } = this._sliderToDate(this.sliderValue);
    this.health.getTree(year, month).subscribe({
      next: data => this._render(data),
      error: err => console.error('tree fetch failed', err),
    });
  }

  private _render(data: TreeNode): void {
    this.treeEmpty = false;
    const innerW = this.width - this.margin.left - this.margin.right;
    const innerH = this.height - this.margin.top - this.margin.bottom;

    const root = d3.hierarchy<TreeNode>(data);
    const treeLayout = d3.tree<TreeNode>().size([innerH, innerW]);
    treeLayout(root);

    // Links
    const linkSel = this.g.selectAll<SVGPathElement, d3.HierarchyLink<TreeNode>>('.link')
      .data(root.links(), (d: d3.HierarchyLink<TreeNode>) =>
        `${d.source.data.name}-${d.target.data.name}`);

    linkSel.enter()
      .append('path')
      .attr('class', 'link')
      .attr('fill', 'none')
      .attr('stroke', '#3d4450')
      .attr('stroke-width', 1.5)
      .merge(linkSel)
      .transition().duration(TRANSITION_DURATION)
      .attr('d', d3.linkHorizontal<d3.HierarchyLink<TreeNode>, d3.HierarchyPointNode<TreeNode>>()
        .x(d => (d as any).y)
        .y(d => (d as any).x) as any);

    linkSel.exit().remove();

    // Nodes
    const nodeSel = this.g.selectAll<SVGGElement, d3.HierarchyPointNode<TreeNode>>('.node')
      .data(root.descendants(), (d: d3.HierarchyNode<TreeNode>) => d.data.name);

    const nodeEnter = nodeSel.enter()
      .append('g')
      .attr('class', 'node')
      .attr('data-name', d => d.data.name)
      .attr('data-id', d => d.data.id)
      .attr('transform', (d: any) => `translate(${d.y},${d.x})`);

    nodeEnter.append('circle');
    nodeEnter.append('text');

    const nodeMerge = nodeEnter.merge(nodeSel);

    nodeMerge.transition().duration(TRANSITION_DURATION)
      .attr('transform', (d: any) => `translate(${d.y},${d.x})`);

    nodeMerge.select<SVGCircleElement>('circle')
      .transition().duration(TRANSITION_DURATION)
      .attr('r', d => this._radius(d.data.health_score))
      .attr('fill', d => d.data.health_score != null
        ? this.colorScale(d.data.health_score)
        : '#484f58')
      .attr('stroke', '#58a6ff')
      .attr('stroke-width', d => d.data.partial ? 1 : 0);

    nodeMerge.select<SVGTextElement>('text')
      .attr('dy', '0.35em')
      .attr('x', (d: any) => d.children ? -(this._radius(d.data.health_score) + 4) : this._radius(d.data.health_score) + 4)
      .attr('text-anchor', (d: any) => d.children ? 'end' : 'start')
      .attr('fill', '#b0bac5')
      .attr('font-size', '12px')
      .text(d => d.data.name);

    nodeSel.exit().remove();
  }

  private _radius(score: number | null): number {
    if (score == null) return 6;
    return 4 + (score / 100) * 20;
  }

  private _applyLiveUpdate(update: { language_id: number; new_score: number; sub_score_type: string }): void {
    const node = this.g.select<SVGGElement>(`.node[data-id="${update.language_id}"]`);
    if (node.empty()) return;

    node.select<SVGCircleElement>('circle')
      .transition().duration(TRANSITION_DURATION)
      .attr('r', () => this._radius(update.new_score))
      .attr('fill', () => this.colorScale(update.new_score));
  }
}
