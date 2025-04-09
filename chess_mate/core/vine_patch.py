"""
Patch for vine module to work with Python 3.12 which removed formatargspec
"""

import inspect
import sys
import warnings

def patch_vine():
    """
    Apply a monkey patch to the vine.five module to fix 
    compatibility with Python 3.12 which removed formatargspec
    """
    try:
        import vine.five
        
        # Check if we're on Python 3.12+ where formatargspec was removed
        if not hasattr(inspect, 'formatargspec'):
            # Define our own formatargspec function
            def formatargspec(args, varargs=None, varkw=None, defaults=None,
                              kwonlyargs=(), kwonlydefaults={}, annotations={}):
                """
                Replacement for inspect.formatargspec that was removed in Python 3.12
                """
                # Convert args to strings
                args = [str(arg) for arg in args]
                
                # Format basic arguments
                parts = []
                if args:
                    parts.append(", ".join(args))
                if varargs:
                    parts.append(f"*{varargs}")
                if kwonlyargs:
                    if not varargs:
                        parts.append("*")
                    parts.extend([f"{arg}={kwonlydefaults.get(arg, 'None')}" 
                                for arg in kwonlyargs])
                if varkw:
                    parts.append(f"**{varkw}")
                
                # Format the full signature
                sig = "(" + ", ".join(parts) + ")"
                
                # Add return annotation if present
                if annotations and 'return' in annotations:
                    sig += f" -> {annotations['return']}"
                    
                return sig
            
            # Monkey patch the inspect module temporarily
            inspect.formatargspec = formatargspec
            
            # Since getargspec is also deprecated, provide a fallback using getfullargspec
            if not hasattr(inspect, 'getargspec'):
                def getargspec(func):
                    """
                    Replacement for inspect.getargspec that was removed
                    Uses getfullargspec and converts to the old format
                    """
                    args, varargs, varkw, defaults, kwonlyargs, kwonlydefaults, annotations = \
                        inspect.getfullargspec(func)
                    return inspect.ArgSpec(args, varargs, varkw, defaults)
                
                inspect.getargspec = getargspec
            
            # Set the formatargspec in vine.five
            vine.five.formatargspec = formatargspec
            vine.five.getargspec = getargspec if hasattr(inspect, 'getargspec') else inspect.getargspec
            
            warnings.warn(
                "Applied monkey patch for vine.five to work with Python 3.12+. "
                "This is a temporary fix until the library is updated.",
                RuntimeWarning
            )
            
            return True
    except ImportError:
        return False
    except Exception as e:
        warnings.warn(f"Failed to patch vine module: {e}", RuntimeWarning)
        return False

# Auto-apply the patch when this module is imported
patch_applied = patch_vine() 