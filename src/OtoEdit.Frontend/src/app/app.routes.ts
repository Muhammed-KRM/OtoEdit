import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () => import('./features/project-list/project-list.component').then(m => m.ProjectListComponent)
  },
  {
    path: 'project/:id',
    loadComponent: () => import('./features/project-detail/project-detail.component').then(m => m.ProjectDetailComponent)
  },
  {
    path: 'project/:id/editor',
    loadComponent: () => import('./features/editor/editor.component').then(m => m.EditorComponent)
  },
  {
    path: 'project/:id/render/:renderJobId',
    loadComponent: () => import('./features/render-result/render-result.component').then(m => m.RenderResultComponent)
  },
  {
    path: '**',
    redirectTo: ''
  }
];
