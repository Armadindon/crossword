import sys
import random

from crossword import *


class CrosswordCreator():

    def __init__(self, crossword):
        """
        Create new CSP crossword generate.
        """
        self.crossword = crossword
        self.domains = {
            var: self.crossword.words.copy()
            for var in self.crossword.variables
        }

    def letter_grid(self, assignment):
        """
        Return 2D array representing a given assignment.
        """
        letters = [
            [None for _ in range(self.crossword.width)]
            for _ in range(self.crossword.height)
        ]
        for variable, word in assignment.items():
            direction = variable.direction
            for k in range(len(word)):
                i = variable.i + (k if direction == Variable.DOWN else 0)
                j = variable.j + (k if direction == Variable.ACROSS else 0)
                letters[i][j] = word[k]
        return letters

    def print(self, assignment):
        """
        Print crossword assignment to the terminal.
        """
        letters = self.letter_grid(assignment)
        for i in range(self.crossword.height):
            for j in range(self.crossword.width):
                if self.crossword.structure[i][j]:
                    print(letters[i][j] or " ", end="")
                else:
                    print("█", end="")
            print()

    def save(self, assignment, filename):
        """
        Save crossword assignment to an image file.
        """
        from PIL import Image, ImageDraw, ImageFont
        cell_size = 100
        cell_border = 2
        interior_size = cell_size - 2 * cell_border
        letters = self.letter_grid(assignment)

        # Create a blank canvas
        img = Image.new(
            "RGBA",
            (self.crossword.width * cell_size,
             self.crossword.height * cell_size),
            "black"
        )
        font = ImageFont.truetype("assets/fonts/OpenSans-Regular.ttf", 80)
        draw = ImageDraw.Draw(img)

        for i in range(self.crossword.height):
            for j in range(self.crossword.width):

                rect = [
                    (j * cell_size + cell_border,
                     i * cell_size + cell_border),
                    ((j + 1) * cell_size - cell_border,
                     (i + 1) * cell_size - cell_border)
                ]
                if self.crossword.structure[i][j]:
                    draw.rectangle(rect, fill="white")
                    if letters[i][j]:
                        w, h = draw.textsize(letters[i][j], font=font)
                        draw.text(
                            (rect[0][0] + ((interior_size - w) / 2),
                             rect[0][1] + ((interior_size - h) / 2) - 10),
                            letters[i][j], fill="black", font=font
                        )

        img.save(filename)

    def solve(self):
        """
        Enforce node and arc consistency, and then solve the CSP.
        """
        self.enforce_node_consistency()
        self.ac3()
        return self.backtrack(dict())

    def enforce_node_consistency(self):
        """
        Update `self.domains` such that each variable is node-consistent.
        (Remove any values that are inconsistent with a variable's unary
         constraints; in this case, the length of the word.)
        """
        new_domains = {}
        for val, domain in self.domains.items():
            new_domains[val] = set(filter(lambda x: len(x) == val.length, domain))
        
        self.domains = new_domains

    def revise(self, x, y):
        """
        Make variable `x` arc consistent with variable `y`.
        To do so, remove values from `self.domains[x]` for which there is no
        possible corresponding value for `y` in `self.domains[y]`.

        Return True if a revision was made to the domain of `x`; return
        False if no revision was made.
        """

        domain_x, domain_y = self.domains[x], self.domains[y]
        
        x_i,y_i = self.crossword.overlaps[x,y]
        new_domain_x = []
        for word_x in domain_x:
            compatible_words = [word_y for word_y in domain_y if word_x[x_i] == word_y[y_i]]
            if len(compatible_words) != 0:
                new_domain_x.append(word_x)

        self.domains[x] = new_domain_x

        return len(new_domain_x) != len(domain_x)

    def ac3(self, arcs=None):
        """
        Update `self.domains` such that each variable is arc consistent.
        If `arcs` is None, begin with initial list of all arcs in the problem.
        Otherwise, use `arcs` as the initial list of arcs to make consistent.

        Return True if arc consistency is enforced and no domains are empty;
        return False if one or more domains end up empty.
        """
        if arcs is None:
            arcs = [(x,y) for x in self.domains.keys() for y in self.crossword.neighbors(x)]
        
        queue = arcs.copy()

        while len(queue) != 0:
            x,y = queue.pop(0)
            if self.revise(x,y):
                if len(self.domains[x]) == 0:
                    return False
                
                for neighbor in self.crossword.neighbors(x):
                    queue.append((x,neighbor))
        
        return True
                

    def assignment_complete(self, assignment):
        """
        Return True if `assignment` is complete (i.e., assigns a value to each
        crossword variable); return False otherwise.
        """
        for var in self.crossword.variables:
            if var not in assignment:
                return False

        return True

    def consistent(self, assignment):
        """
        Return True if `assignment` is consistent (i.e., words fit in crossword
        puzzle without conflicting characters); return False otherwise.
        """
        present_words = []
        for var, word in assignment.items():
            if word in present_words or len(word) != var.length:
                return False
            
            present_words.append(word)

            for neighbor in self.crossword.neighbors(var):
                neighbor_word = assignment[neighbor]

                if neighbor_word == None:
                    continue

                var_i, neighbor_i = self.crossword.overlaps[var,neighbor]
                if word[var_i] != neighbor_word[neighbor_i]:
                    return False
        
        return True

    def order_domain_values(self, var, assignment):
        """
        Return a list of values in the domain of `var`, in order by
        the number of values they rule out for neighboring variables.
        The first value in the list, for example, should be the one
        that rules out the fewest values among the neighbors of `var`.
        """
        best_value = {value: 0 for value in self.domains[var]}
        for neighbor in self.crossword.neighbors(var):
            if neighbor not in assignment:
                continue
            neighbor_word = assignment[neighbor]
            if neighbor_word not in best_value:
                continue
            best_value[neighbor_word] += 1

        values = list(best_value.keys())
        values.sort(key=lambda x: best_value[x])
        return values

    def select_unassigned_variable(self, assignment):
        """
        Return an unassigned variable not already part of `assignment`.
        Choose the variable with the minimum number of remaining values
        in its domain. If there is a tie, choose the variable with the highest
        degree. If there is a tie, any of the tied variables are acceptable
        return values.
        """
        remaining_variables = [variable for variable in self.crossword.variables if variable not in assignment.keys()]
        number_of_values_by_domains = {variable : len(self.domains[variable]) for variable in remaining_variables}
        remaining_variables_min_remaining_values = [variable for variable in remaining_variables if number_of_values_by_domains[variable] == min(number_of_values_by_domains.values())]
        
        if len(remaining_variables) == 1:
            return remaining_variables_min_remaining_values[0]
        
        degree_by_variable = {variable : len(self.crossword.neighbors(variable)) for variable in remaining_variables_min_remaining_values}
        remaining_min_degree = [variable for variable in remaining_variables_min_remaining_values if degree_by_variable[variable] == min(degree_by_variable.values())]
        
        return random.choice(remaining_min_degree)

    def backtrack(self, assignment):
        """
        Using Backtracking Search, take as input a partial assignment for the
        crossword and return a complete assignment if possible to do so.

        `assignment` is a mapping from variables (keys) to words (values).

        If no assignment is possible, return None.
        """

        # We chose which variables we will bactrack
        if self.assignment_complete(assignment):
            return assignment if self.consistent(assignment) else None

        treated_var = self.select_unassigned_variable(assignment)
        possible_values = self.order_domain_values(treated_var, assignment)
        
        for possible_value in possible_values:
            possible_assignment = assignment.copy()
            possible_assignment[treated_var] = possible_value

            new_assignment = self.backtrack(possible_assignment)
            if new_assignment != None:
                return new_assignment        
        



def main():

    # Check usage
    if len(sys.argv) not in [3, 4]:
        sys.exit("Usage: python generate.py structure words [output]")

    # Parse command-line arguments
    structure = sys.argv[1]
    words = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) == 4 else None

    # Generate crossword
    crossword = Crossword(structure, words)
    creator = CrosswordCreator(crossword)
    assignment = creator.solve()

    # Print result
    if assignment is None:
        print("No solution.")
    else:
        creator.print(assignment)
        if output:
            creator.save(assignment, output)


if __name__ == "__main__":
    main()
