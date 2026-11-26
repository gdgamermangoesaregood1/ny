from collections import defaultdict
import heapq
import unittest

import pygame

from enemyai import Enemy, Navigation
from levels import create_levels
from physics import Body
from Platstart import Game, HEIGHT, PLAYER_SPEED, Player, WIDTH


class PhysicsTests(unittest.TestCase):
    def test_fast_fall_lands_on_first_thin_platform(self):
        platforms = [pygame.Rect(0, 100, 300, 10), pygame.Rect(0, 200, 300, 10)]
        body = Body(50, 20, 40, 40)
        body.vel_y = 120
        body.step(0, False, platforms, 300)
        self.assertEqual(body.rect.bottom, 100)
        self.assertTrue(body.on_ground)

    def test_jump_hits_ceiling_and_cannot_jump_again_in_air(self):
        platforms = [pygame.Rect(0, 200, 300, 20), pygame.Rect(0, 145, 300, 10)]
        body = Body(50, 160, 40, 40)
        body.on_ground = True
        body.step(0, True, platforms, 300)
        self.assertEqual(body.rect.top, 155)
        self.assertEqual(body.vel_y, 0)
        body.step(0, True, platforms, 300)
        self.assertGreater(body.vel_y, 0)


class LevelNavigationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.levels = create_levels()
        cls.navigations = [
            Navigation(level.platforms, level.width, level.height)
            for level in cls.levels
        ]

    def test_every_level_coin_and_exit_is_physically_reachable(self):
        self.assertEqual(len(self.levels), 11)
        for level, nav in zip(self.levels, self.navigations):
            with self.subTest(level=level.name):
                self.assertGreater(level.width, WIDTH * 2)
                self.assertGreater(level.height, HEIGHT)
                start = nav.nearest_node(0, level.player_spawn[0])
                seen = {start}
                pending = [start]
                while pending:
                    for edge in nav.graph[pending.pop()]:
                        if edge.target not in seen:
                            seen.add(edge.target)
                            pending.append(edge.target)
                self.assertEqual(len(seen), len(nav.nodes))
                targets = []
                for coin in level.coin_spawns:
                    target = Player(coin.centerx - 20, coin.bottom - 50)
                    platform = next(
                        i for i, p in enumerate(level.platforms)
                        if p.top == coin.bottom + 10 and p.left <= coin.centerx <= p.right
                    )
                    targets.append(nav.nearest_node(platform, target.rect.x))
                targets.append(nav.nearest_node(0, level.exit.x))
                # Player height and speed differ: plan and replay actual player jumps.
                player_nav = Navigation(
                    level.platforms, level.width, level.height,
                    body_height=50, speed=PLAYER_SPEED,
                )
                player_start = player_nav.nearest_node(0, level.player_spawn[0])
                for enemy_goal in targets:
                    destination = nav.nodes[enemy_goal]
                    goal = player_nav.nearest_node(destination.platform, destination.x)
                    path = player_nav.find_path(player_start, goal)
                    self.assertIsNotNone(path)
                    player = Player(player_nav.nodes[player_start].x, level.platforms[0].top - 50)
                    player.on_ground = True
                    for edge in path:
                        for dx, jump in edge.actions:
                            player.step(dx, jump, level.platforms, level.width)
                        expected = player_nav.nodes[edge.target]
                        self.assertEqual(player.rect.x, expected.x)
                        self.assertEqual(nav.support(player.rect), expected.platform)
                        self.assertTrue(player.on_ground)

    def test_every_graph_edge_replays_to_its_exact_destination(self):
        for level, nav in zip(self.levels, self.navigations):
            with self.subTest(level=level.name):
                for source, edges in nav.graph.items():
                    for edge in edges:
                        body = nav.body_at(source)
                        for dx, jump in edge.actions:
                            body.step(dx, jump, level.platforms, level.width)
                            self.assertEqual(body.rect.collidelist(level.platforms), -1)
                        self.assertEqual(body.rect, nav.body_at(edge.target).rect)
                        self.assertTrue(body.on_ground)

    def test_astar_matches_shortest_travel_time(self):
        nav = self.navigations[-1]
        start = nav.nearest_node(0, 80)
        goal = nav.platform_nodes[len(nav.platforms) - 1][-1]
        costs = {start: 0}
        pending = [(0, start)]
        while pending:
            cost, node = heapq.heappop(pending)
            if node == goal:
                break
            if cost != costs[node]:
                continue
            for edge in nav.graph[node]:
                candidate = cost + len(edge.actions)
                if candidate < costs.get(edge.target, float("inf")):
                    costs[edge.target] = candidate
                    heapq.heappush(pending, (candidate, edge.target))
        path = nav.find_path(start, goal)
        self.assertIsNotNone(path)
        self.assertEqual(sum(len(edge.actions) for edge in path), costs[goal])

    def test_enemy_takes_detour_jumps_then_replans_for_ground_target(self):
        platforms = [pygame.Rect(0, 600, 900, 40), pygame.Rect(100, 480, 200, 20)]
        nav = Navigation(platforms, 900, 640)
        enemy = Enemy(nav, (200, 560))
        player = Player(200, 430)
        player.on_ground = True
        farthest_distance = 0
        for _ in range(1000):
            enemy.update(player)
            farthest_distance = max(farthest_distance, abs(enemy.rect.x - player.rect.x))
            if enemy.rect.colliderect(player.rect):
                break
        self.assertGreaterEqual(farthest_distance, 100)
        self.assertTrue(enemy.rect.colliderect(player.rect))
        player.rect.topleft = (700, 550)
        for _ in range(1000):
            enemy.update(player)
            if enemy.rect.colliderect(player.rect):
                break
        self.assertTrue(enemy.rect.colliderect(player.rect))
        self.assertEqual(nav.support(enemy.rect), 0)

    def test_unreachable_target_and_airborne_prediction(self):
        platforms = [pygame.Rect(0, 600, 900, 40), pygame.Rect(100, 100, 200, 20)]
        nav = Navigation(platforms, 900, 640)
        enemy = Enemy(nav, (100, 560))
        player = Player(150, 50)
        player.on_ground = True
        for _ in range(20):
            enemy.update(player)
        self.assertEqual(enemy.status, "No reachable route")
        self.assertEqual(enemy.rect.bottom, 600)
        player.rect.topleft = (500, 250)
        player.on_ground = False
        self.assertEqual(nav.nodes[nav.target_node(player)].platform, 0)

    def test_enemy_reaches_high_target_and_returns_to_ground_in_every_world(self):
        for level, nav in zip(self.levels, self.navigations):
            with self.subTest(level=level.name):
                enemy = Enemy(nav, level.enemy_spawn)
                top = level.platforms[-1]
                player = Player(top.centerx - 20, top.top - 50)
                player.on_ground = True
                for destination in (player.rect.topleft, level.player_spawn):
                    player.rect.topleft = destination
                    for _ in range(6000):
                        enemy.update(player)
                        self.assertEqual(enemy.rect.collidelist(level.platforms), -1)
                        if enemy.rect.colliderect(player.rect):
                            break
                    self.assertTrue(
                        enemy.rect.colliderect(player.rect),
                        (enemy.status, enemy.rect, player.rect),
                    )

    def make_game(self):
        game = Game.__new__(Game)
        game.levels = self.levels
        game.navigation_cache = dict(enumerate(self.navigations))
        game.restart()
        return game

    def test_coin_gate_all_level_transitions_and_final_win(self):
        game = self.make_game()
        keys = defaultdict(bool)
        total = 0
        for index, level in enumerate(self.levels):
            self.assertEqual(game.level_index, index)
            game.player.rect.bottomleft = (level.exit.x, level.platforms[0].top)
            game.update(keys)
            self.assertEqual(game.level_index, index, "Exit must stay locked while coins remain")
            for coin in game.coins[:]:
                game.player.rect.topleft = (coin.x, coin.y - 20)
                game.player.vel_y = 0
                game.player.on_ground = False
                game.enemy.rect.topleft = (level.width - 200, level.platforms[0].top - 40)
                game.enemy.actions.clear()
                game.enemy.route.clear()
                game.update(keys)
                total += 1
            self.assertFalse(game.coins)
            self.assertEqual(game.total_coins, total)
            game.player.rect.bottomleft = (level.exit.x, level.platforms[0].top)
            game.player.vel_y = 0
            game.update(keys)
        self.assertTrue(game.completed)
        game.update(keys)
        self.assertEqual(game.total_coins, total)
        game.restart()
        self.assertFalse(game.completed)
        self.assertEqual(game.level_index, 0)
        self.assertEqual(game.total_coins, 0)

    def test_death_on_later_level_restarts_first_and_loses_all_coins(self):
        for cause in ("enemy", "fall"):
            with self.subTest(cause=cause):
                game = self.make_game()
                game.load_level(5)
                game.total_coins = 30
                game.coins.pop()
                if cause == "enemy":
                    game.player.rect.topleft = game.enemy.rect.topleft
                else:
                    game.player.rect.top = game.level.height
                game.update(defaultdict(bool))
                self.assertEqual(game.level_index, 0)
                self.assertEqual(game.total_coins, 0)
                self.assertEqual(game.coins, self.levels[0].coin_spawns)
                self.assertEqual(game.player.rect.topleft, self.levels[0].player_spawn)

    def test_camera_tracks_both_axes_and_stays_inside_world(self):
        game = self.make_game()
        game.player.rect.topleft = (1200, 300)
        x, y = game.camera()
        self.assertGreater(x, 0)
        self.assertGreater(y, 0)
        self.assertLessEqual(x, game.level.width - WIDTH)
        self.assertLessEqual(y, game.level.height - HEIGHT)
        game.player.rect.topleft = (0, 0)
        self.assertEqual(game.camera(), (0, 0))
        game.player.rect.bottomright = (game.level.width, game.level.height)
        self.assertEqual(game.camera(), (game.level.width - WIDTH, game.level.height - HEIGHT))


if __name__ == "__main__":
    unittest.main()
