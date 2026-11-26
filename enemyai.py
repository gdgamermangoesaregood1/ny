from collections import deque
from dataclasses import dataclass
import heapq
import math

from physics import Body, GRAVITY, JUMP_STRENGTH


ENEMY_SPEED = 3
ENEMY_SIZE = 40
NODE_SPACING = 40


@dataclass(frozen=True)
class Node:
    platform: int
    x: int


@dataclass(frozen=True)
class Transition:
    target: int
    actions: tuple[tuple[int, bool], ...]


class Navigation:
    def __init__(self, platforms, world_width, world_height,
                 body_height=ENEMY_SIZE, speed=ENEMY_SPEED):
        self.platforms = platforms
        self.world_width = world_width
        self.world_height = world_height
        self.body_height = body_height
        self.speed = speed
        self.nodes = []
        self.platform_nodes = {}
        self.graph = {}
        self.max_flight_frames = int(
            2 * abs(JUMP_STRENGTH) / GRAVITY
            + math.sqrt(2 * world_height / GRAVITY) + 10
        )
        for platform_index, platform in enumerate(platforms):
            if platform.width < ENEMY_SIZE:
                continue
            right = platform.right - ENEMY_SIZE
            positions = list(range(platform.left, right + 1, NODE_SPACING))
            if positions[-1] != right:
                positions.append(right)
            for x in positions:
                body = Body(x, platform.top - body_height, ENEMY_SIZE, body_height)
                if body.rect.collidelist(platforms) == -1:
                    node_index = len(self.nodes)
                    self.nodes.append(Node(platform_index, x))
                    self.platform_nodes.setdefault(platform_index, []).append(node_index)
        for index in range(len(self.nodes)):
            self.graph[index] = self._transitions(index)

    def support(self, rect):
        for index, platform in enumerate(self.platforms):
            if (rect.bottom == platform.top
                    and rect.right > platform.left and rect.left < platform.right):
                return index
        return None

    def nearest_node(self, platform, x):
        candidates = self.platform_nodes.get(platform, [])
        return min(candidates, key=lambda index: abs(self.nodes[index].x - x)) if candidates else None

    def body_at(self, node_index):
        node = self.nodes[node_index]
        body = Body(node.x, self.platforms[node.platform].top - self.body_height,
                    ENEMY_SIZE, self.body_height)
        body.on_ground = True
        return body

    def _walk_to(self, body, target_x, support):
        actions = []
        while body.rect.x != target_x:
            dx = max(-self.speed, min(self.speed, target_x - body.rect.x))
            previous_x = body.rect.x
            body.step(dx, False, self.platforms, self.world_width)
            if (body.rect.x == previous_x or not body.on_ground
                    or self.support(body.rect) != support):
                return None
            actions.append((dx, False))
        return actions

    def _flight(self, source, dx, jump):
        body = self.body_at(source)
        actions = []
        for frame in range(self.max_flight_frames):
            previous = body.rect.copy()
            body.step(dx, jump and frame == 0, self.platforms, self.world_width)
            actions.append((dx, jump and frame == 0))
            if body.rect.top >= self.world_height:
                return None
            support = self.support(body.rect)
            if body.on_ground and (jump or support != self.nodes[source].platform):
                target = self.nearest_node(support, body.rect.x)
                if target is None or target == source:
                    return None
                tail = self._walk_to(body, self.nodes[target].x, support)
                if tail is not None:
                    return Transition(target, tuple(actions + tail))
                return None
            if body.on_ground and body.rect == previous:
                return None
        return None

    def _transitions(self, source):
        node = self.nodes[source]
        siblings = self.platform_nodes[node.platform]
        position = siblings.index(source)
        edges = []
        for neighbor_position in (position - 1, position + 1):
            if 0 <= neighbor_position < len(siblings):
                target = siblings[neighbor_position]
                actions = self._walk_to(self.body_at(source), self.nodes[target].x, node.platform)
                if actions:
                    edges.append(Transition(target, tuple(actions)))
        for direction in (-1, 0, 1):
            edge = self._flight(source, direction * self.speed, True)
            if edge:
                edges.append(edge)
        if position in (0, len(siblings) - 1) and node.platform != 0:
            for direction in (-1, 1):
                edge = self._flight(source, direction * self.speed, False)
                if edge:
                    edges.append(edge)
        return edges

    def find_path(self, start, goal):
        # Horizontal travel time is a lower bound even for jumps and long falls.
        def heuristic(index):
            return abs(self.nodes[index].x - self.nodes[goal].x) / self.speed

        frontier = [(heuristic(start), 0, start)]
        costs = {start: 0}
        previous = {}
        while frontier:
            _, cost, current = heapq.heappop(frontier)
            if cost != costs[current]:
                continue
            if current == goal:
                path = []
                while current != start:
                    current, edge = previous[current]
                    path.append(edge)
                return list(reversed(path))
            for edge in self.graph[current]:
                next_cost = cost + len(edge.actions)
                if next_cost < costs.get(edge.target, math.inf):
                    costs[edge.target] = next_cost
                    previous[edge.target] = (current, edge)
                    heapq.heappush(frontier, (
                        next_cost + heuristic(edge.target), next_cost, edge.target,
                    ))
        return None

    def target_node(self, player):
        support = self.support(player.rect)
        if support is None:
            # Predict where an airborne target would land, rather than chasing empty sky.
            prediction = Body(player.rect.x, player.rect.y, player.rect.width, player.rect.height)
            prediction.vel_y = player.vel_y
            for _ in range(self.max_flight_frames):
                prediction.step(0, False, self.platforms, self.world_width)
                if prediction.on_ground:
                    support = self.support(prediction.rect)
                    break
                if prediction.rect.top >= self.world_height:
                    break
        return self.nearest_node(support, player.rect.x)


class Enemy(Body):
    def __init__(self, navigation, spawn):
        super().__init__(*spawn, ENEMY_SIZE, ENEMY_SIZE)
        self.navigation = navigation
        self.on_ground = navigation.support(self.rect) is not None
        self.actions = deque()
        self.route = deque()
        self.goal = None
        self.status = "Finding route"

    def update(self, player):
        navigation = self.navigation
        if self.actions:
            dx, jump = self.actions.popleft()
            self.step(dx, jump, navigation.platforms, navigation.world_width)
            return
        if not self.on_ground:
            self.step(0, False, navigation.platforms, navigation.world_width)
            return

        goal = navigation.target_node(player)
        support = navigation.support(self.rect)
        start = navigation.nearest_node(support, self.rect.x)
        if start is None or goal is None:
            self.status = "No reachable route"
            self.step(0, False, navigation.platforms, navigation.world_width)
            return

        if goal != self.goal:
            self.route.clear()
            self.goal = goal
        if self.rect.x != navigation.nodes[start].x and start != goal:
            dx = max(-ENEMY_SPEED, min(ENEMY_SPEED, navigation.nodes[start].x - self.rect.x))
            self.step(dx, False, navigation.platforms, navigation.world_width)
            return
        if start == goal:
            self.route.clear()
            self.status = "Chasing"
            dx = max(-ENEMY_SPEED, min(ENEMY_SPEED, player.rect.centerx - self.rect.centerx))
            self.step(dx, False, navigation.platforms, navigation.world_width)
            return
        if not self.route:
            path = navigation.find_path(start, goal)
            if path is None:
                self.status = "No reachable route"
                self.step(0, False, navigation.platforms, navigation.world_width)
                return
            self.route.extend(path)
        self.status = "Following A* route"
        self.actions.extend(self.route.popleft().actions)
        dx, jump = self.actions.popleft()
        self.step(dx, jump, navigation.platforms, navigation.world_width)

    def draw(self, surface, camera):
        super().draw(surface, (100, 40, 140), camera)
