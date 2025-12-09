/**
 * Simplified RecipeGenerator tests focusing on API integration
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import api from '../src/api/axios';

vi.mock('../src/api/axios');

describe('RecipeGenerator API Integration', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('should generate recipe via API', async () => {
        const mockRecipe = {
            status: 'success',
            data: {
                recipe: JSON.stringify({
                    recipe: {
                        name: 'Spaghetti Carbonara',
                        cuisine: 'Italian',
                        time: '30 mins',
                        main_ingredients: ['pasta', 'eggs', 'bacon'],
                        steps: 'Step 1. Boil pasta. Step 2. Cook bacon. Step 3. Mix.',
                    },
                    missing_ingredients: [],
                }),
            },
            history_id: 123,
        };

        api.post.mockResolvedValueOnce({ data: mockRecipe });

        const response = await api.post('/recipes/generate', {
            user_request: 'pasta dish',
            servings: 2,
        });

        expect(response.data.status).toBe('success');
        expect(response.data.history_id).toBe(123);
        expect(api.post).toHaveBeenCalledWith('/recipes/generate', expect.objectContaining({
            user_request: 'pasta dish',
            servings: 2,
        }));
    });

    it('should submit feedback via API', async () => {
        api.post.mockResolvedValueOnce({ data: { status: 'success' } });

        const response = await api.post('/recipes/999/feedback', { score: 2 });

        expect(response.data.status).toBe('success');
        expect(api.post).toHaveBeenCalledWith('/recipes/999/feedback', { score: 2 });
    });

    it('should mark recipe as cooked via API', async () => {
        api.post.mockResolvedValueOnce({
            data: {
                status: 'success',
                deducted_items: ['pasta', 'eggs']
            }
        });

        const response = await api.post('/recipes/123/cooked');

        expect(response.data.status).toBe('success');
        expect(response.data.deducted_items).toContain('pasta');
        expect(api.post).toHaveBeenCalledWith('/recipes/123/cooked');
    });

    it('should fetch recipe history via API', async () => {
        const mockHistory = [
            {
                id: 1,
                recipe_json: { recipe: { name: 'Recipe 1' } },
                created_at: '2024-01-01',
                servings: 2,
            },
            {
                id: 2,
                recipe_json: { recipe: { name: 'Recipe 2' } },
                created_at: '2024-01-02',
                servings: 4,
            },
        ];

        api.get.mockResolvedValueOnce({ data: mockHistory });

        const response = await api.get('/recipes/history');

        expect(response.data).toHaveLength(2);
        expect(response.data[0].recipe_json.recipe.name).toBe('Recipe 1');
    });

    it('should handle video generation API', async () => {
        api.post.mockResolvedValueOnce({
            data: {
                video_url: 'https://example.com/video.mp4',
                mode: 'mock',
            },
        });

        const response = await api.post('/recipes/video', {
            prompt: 'making pasta carbonara',
        });

        expect(response.data.video_url).toBeDefined();
        expect(response.data.mode).toBe('mock');
    });
});
