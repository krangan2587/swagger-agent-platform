class OutputPackagerError(Exception):
    """Raised when Stage 5 cannot produce a complete, consistent project.
    Per Section 7.5: 'partial output is not left in place.'"""
