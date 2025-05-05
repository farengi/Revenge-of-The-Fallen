# server.py
from flask import Flask, request, jsonify, render_template, send_from_directory
import os
from app.controllers.simulation import ProgrammableMatterSimulation

app = Flask(__name__, static_folder='static')
simulation = ProgrammableMatterSimulation(width=12, height=12)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)


@app.route('/api/state', methods=['GET'])
def get_state():
    # Get the current state of the simulation
    state = simulation.get_state()
    return jsonify(state)

@app.route('/api/transform', methods=['POST'])
def transform():
    try:
        # Get request data
        data = request.json
        
        # Extract parameters
        algorithm = data.get('algorithm', 'astar')
        shape = data.get('shape', 'square')
        num_elements = data.get('num_elements', 8)
        topology = data.get('topology', 'vonNeumann')
        movement = data.get('movement', 'sequential')
        control_mode = data.get('control_mode', 'centralized')
        collision = data.get('collision', True)
        
        print("="*50)
        print(f"REQUEST PARAMETERS:")
        print(f"  Shape: {shape}")
        print(f"  Algorithm: {algorithm}")
        print(f"  Topology: {topology}")
        print(f"  Movement: {movement}")
        print(f"  Control Mode: {control_mode}")
        print(f"  Elements: {num_elements}")
        print("="*50)
        
        # Initialize the simulation with the specified number of elements
        elements = simulation.initialize_elements(num_elements)
        
        print("INITIAL ELEMENT POSITIONS:")
        for eid, element in simulation.controller.elements.items():
            print(f"  Element {eid}: ({element.x}, {element.y})")
        
        # Set the target shape
        targets = simulation.set_target_shape(shape, num_elements)
        
        print("TARGET POSITIONS:")
        for i, (tx, ty) in enumerate(targets):
            print(f"  Target {i}: ({tx}, {ty})")
        
        # Run the transformation - now supports minimax, expectimax, and adaptive
        result = simulation.transform(
            algorithm=algorithm,
            topology=topology,
            movement=movement,
            control_mode=control_mode
        )
        
        if not result["moves"]:
            print("WARNING: No moves were generated. The transformation may have failed.")
        else:
            print("TRANSFORMATION RESULT:")
            print(f"  Moves: {len(result['moves'])}")
            print(f"  Nodes explored: {result.get('nodes_explored', 0)}")
            
            # Detailed move logging
            print("MOVES (Backend format):")
            for i, move in enumerate(result['moves']):
                print(f"  Move {i}: Agent {move['agentId']} from {move['from']} to {move['to']}")
        
        # Format the moves for the frontend with explicit coordinate handling
        frontend_moves = []
        for move in result['moves']:
            # Create adjusted coordinates with both X and Y fixes
            # Move left by 1 column and up by 1 row
            frontend_move = {
                'agentId': move['agentId'],
                'from': {'x': move['from'][0] - 1, 'y': move['from'][1] - 1},  # Subtract 1 from both x and y
                'to': {'x': move['to'][0] - 1, 'y': move['to'][1] - 1}         # Subtract 1 from both x and y
            }
            frontend_moves.append(frontend_move)
        
        # Log frontend moves
        print("MOVES (Frontend format):")
        for i, move in enumerate(frontend_moves):
            print(f"  Move {i}: Agent {move['agentId']} from ({move['from']['x']},{move['from']['y']}) to ({move['to']['x']},{move['to']['y']})")
        
        # Final element positions
        print("FINAL ELEMENT POSITIONS:")
        for eid, element in simulation.controller.elements.items():
            if hasattr(element, 'target_x') and element.target_x is not None:
                at_target = element.x == element.target_x and element.y == element.target_y
                status = "AT TARGET" if at_target else "NOT AT TARGET"
                print(f"  Element {eid}: ({element.x}, {element.y}) -> Target: ({element.target_x}, {element.target_y}) {status}")
            else:
                print(f"  Element {eid}: ({element.x}, {element.y}) -> No target assigned")
        
        # Prepare the response
        response = {
            'success': True if frontend_moves else False,
            'moves': frontend_moves,
            'time': result['time'],
            'nodes': result.get('nodes_explored', 0),
            'message': 'Transformation completed successfully' if frontend_moves else 'No valid moves found',
            'algorithm_used': result.get('algorithm_used', algorithm)  # Include which algorithm was actually used
        }
        
        return jsonify(response)
    
    except Exception as e:
        import traceback
        print(f"ERROR during transformation: {str(e)}")
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'moves': [],
            'time': 0,
            'nodes': 0,
            'message': f'Error during transformation: {str(e)}'
        }), 500  # Return 500 status code for server errors
 
    
@app.route('/api/reset', methods=['POST'])
def reset():
    # Reset the simulation
    simulation.reset()
    return jsonify({'success': True, 'message': 'Simulation reset'})

@app.route('/api/shapes', methods=['GET'])
def get_available_shapes():
    # Return available shape types
    shapes = ['square', 'circle', 'triangle', 'heart']
    return jsonify({'shapes': shapes})

@app.route('/api/algorithms', methods=['GET'])
def get_available_algorithms():
    # Return available algorithms with descriptions
    algorithms = {
        'astar': 'A* Search - Optimal pathfinding using Manhattan distance heuristic',
        'bfs': 'Breadth-First Search - Complete search guaranteeing shortest path',
        'greedy': 'Greedy Search - Fast but potentially suboptimal pathfinding',
        'minimax': 'Minimax - Adversarial search for complex environments',
        'expectimax': 'Expectimax - Probabilistic search handling uncertainty',
        'adaptive': 'Adaptive - Dynamic algorithm selection based on environment'
    }
    return jsonify({'algorithms': algorithms})

@app.route('/api/analyze', methods=['POST'])
def analyze_performance():
    """
    Analyze the performance of different algorithms for a specific shape and parameters.
    This endpoint runs multiple transformations with different algorithms and compares results.
    """
    try:
        # Get request data
        data = request.json
        
        # Extract parameters
        shape = data.get('shape', 'square')
        num_elements = data.get('num_elements', 8)
        topology = data.get('topology', 'vonNeumann')
        control_mode = data.get('control_mode', 'centralized')
        
        # Algorithms to compare
        algorithms = ['astar', 'bfs', 'greedy', 'minimax', 'expectimax', 'adaptive']
        
        results = {}
        
        # Run each algorithm
        for alg in algorithms:
            print(f"Testing algorithm: {alg}")
            
            # Reset simulation for clean comparison
            simulation.reset()
            simulation.initialize_elements(num_elements)
            simulation.set_target_shape(shape, num_elements)
            
            # Run transformation
            result = simulation.transform(
                algorithm=alg,
                topology=topology,
                movement='parallel',  # Use parallel for better comparison
                control_mode=control_mode
            )
            
            # Store results
            success_rate = 0
            # Calculate success rate
            total_elements = sum(1 for e in simulation.controller.elements.values() if e.has_target())
            at_target = sum(1 for e in simulation.controller.elements.values() 
                         if e.has_target() and e.x == e.target_x and e.y == e.target_y)
            
            if total_elements > 0:
                success_rate = at_target / total_elements
            
            results[alg] = {
                'success_rate': success_rate,
                'moves': len(result.get('moves', [])),
                'time': result.get('time', 0),
                'nodes_explored': result.get('nodes_explored', 0)
            }
            
            print(f"  Success rate: {success_rate*100:.1f}%")
            print(f"  Moves: {len(result.get('moves', []))}")
            print(f"  Time: {result.get('time', 0):.2f}s")
            
        return jsonify({
            'success': True,
            'results': results,
            'shape': shape,
            'elements': num_elements,
            'topology': topology,
            'control_mode': control_mode
        })
        
    except Exception as e:
        import traceback
        print(f"ERROR during analysis: {str(e)}")
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'message': f'Error during analysis: {str(e)}'
        }), 500

@app.route('/api/deadlock-locations', methods=['POST'])
def analyze_deadlock_locations():
    """
    Identify locations on the grid where deadlocks commonly occur for specific shapes.
    This helps understand challenging areas in the formation process.
    """
    try:
        # Get request data
        data = request.json
        
        # Extract parameters
        shape = data.get('shape', 'square')
        num_elements = data.get('num_elements', 8)
        topology = data.get('topology', 'vonNeumann')
        
        # Number of test runs
        num_runs = data.get('runs', 5)
        
        # Create a grid to track deadlock locations
        deadlock_grid = [[0 for _ in range(simulation.grid.width)] for _ in range(simulation.grid.height)]
        
        # Run multiple transformations and track where elements get stuck
        for run in range(num_runs):
            print(f"Deadlock analysis run {run+1}/{num_runs}")
            
            # Reset simulation
            simulation.reset()
            simulation.initialize_elements(num_elements)
            simulation.set_target_shape(shape, num_elements)
            
            # Use non-adversarial algorithms to better identify natural deadlocks
            simulation.transform(
                algorithm='astar',
                topology=topology,
                movement='parallel',
                control_mode='independent'
            )
            
            # Check which elements didn't reach targets
            for eid, element in simulation.controller.elements.items():
                if element.has_target() and (element.x != element.target_x or element.y != element.target_y):
                    # Increment deadlock counter for this position
                    deadlock_grid[element.y][element.x] += 1
        
        # Prepare result with normalized heatmap
        max_value = max(max(row) for row in deadlock_grid)
        normalized_grid = []
        if max_value > 0:
            normalized_grid = [[cell/max_value for cell in row] for row in deadlock_grid]
        else:
            normalized_grid = deadlock_grid
        
        return jsonify({
            'success': True,
            'deadlock_grid': deadlock_grid,
            'normalized_grid': normalized_grid,
            'max_value': max_value,
            'runs': num_runs
        })
        
    except Exception as e:
        import traceback
        print(f"ERROR during deadlock analysis: {str(e)}")
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'message': f'Error during deadlock analysis: {str(e)}'
        }), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)